"""Fundamentalist Agent for performing fundamental analysis on companies using financial statements and LLMs."""

import json
from datetime import datetime

import yfinance as yf
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import ValidationError
from requests import RequestException

from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings
from nexus_equitygraph.core.text_utils import cleanup_think_tags, clean_json_markdown
from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState
from nexus_equitygraph.tools.financial_tools import get_financial_statements
from nexus_equitygraph.tools.helpers import ensure_sa_suffix
from nexus_equitygraph.tools.indicator_tools import (
    calculate_debt_indicators,
    calculate_efficiency_indicators,
    calculate_growth_indicators,
    calculate_rentability_indicators,
    calculate_valuation_indicators,
    calculate_wealth_distribution,
    get_auditor_info,
    get_company_profile,
    get_company_profile_data,
    get_financial_evolution,
)
from nexus_equitygraph.tools.market_tools import get_company_name_from_ticker, get_current_stock_price


# pylint: disable=too-many-arguments, too-many-locals
class FundamentalistAgent:
    """Agent that performs fundamental analysis on companies using financial statements and LLMs."""

    def __init__(self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm=None) -> None:
        """Initialize the FundamentalistAgent.
        
        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseLanguageModel]): The language model to use. If None, a default will be created.
        """

        self.state = state
        self.prompt_manager = prompt_manager
        # Use configured provider/model from settings, temperature=0 for deterministic output.
        model_name = settings.ollama_model_reasoning or settings.ollama_default_model
        self.llm = llm or create_llm_provider(temperature=0, model_name=model_name)
        self.ticker = state.ticker

    def _identify_company(self) -> tuple[str, str]:
        """Resolves company name and search term.
        
        Returns:
            tuple[str, str]: Company name and search term.
        """

        company_name = get_company_name_from_ticker.invoke({"ticker": self.ticker})
        search_term = ensure_sa_suffix(company_name) if company_name else self.ticker

        return company_name, search_term

    def _fetch_market_data(self, company_name: str, search_term: str) -> tuple[str, float]:
        """Fetches financial statements and current stock price.

        Args:
            company_name (str): The company name.
            search_term (str): The search term (ticker or name).

        Returns:
            tuple[str, float]: Financial statements and current stock price.
        """

        financial_data = get_financial_statements.invoke({"ticker": search_term})

        # Fallback if search with name failed
        if "Erro" in str(financial_data) and company_name:
            financial_data = get_financial_statements.invoke({"ticker": self.ticker})

        current_price = get_current_stock_price.invoke({"ticker": self.ticker})

        return financial_data, current_price

    def _calculate_indicators(self, target_ticker: str, current_price: float) -> tuple[str, str]:
        """Calculates all financial indicators and returns the context string and valuation data.

        Args:
            target_ticker (str): The target ticker.
            current_price (float): The current stock price.

        Returns:
            tuple[str, str]: Context string and valuation data.
        """

        financial_efficiency_data = calculate_efficiency_indicators.invoke({"ticker": target_ticker})
        debt_data = calculate_debt_indicators.invoke({"ticker": target_ticker})
        rentability_data = calculate_rentability_indicators.invoke({"ticker": target_ticker})
        growth_data = calculate_growth_indicators.invoke({"ticker": target_ticker})

        evolution_data = get_financial_evolution.invoke({"ticker": target_ticker})
        auditor_data = get_auditor_info.invoke({"ticker": target_ticker})
        capital_distribution_data = calculate_wealth_distribution.invoke({"ticker": target_ticker})
        profile_data = get_company_profile.invoke({"ticker": target_ticker})

        valuation_data = calculate_valuation_indicators.invoke(
            {"ticker": target_ticker, "current_price": current_price}
        )

        # Combine into a single context string for the LLM input.
        indicators_context = f"""
        {profile_data}
        
        2. Análise Temporal, Auditoria e Social:
        {evolution_data}
        {auditor_data}
        {capital_distribution_data}
        
        3. Indicadores Calculados:
        {financial_efficiency_data}
        {debt_data}
        {rentability_data}
        {growth_data}
        {valuation_data}
        """

        return indicators_context, valuation_data

    def _prepare_llm_context(
        self,
        company_name: str,
        current_price: float,
        financial_data: str,
        indicators_context: str,
    ) -> str:
        """Formats the context message for the LLM.
        
        Args:
            company_name (str): The company name.
            current_price (float): The current stock price.
            financial_data (str): Financial statements.
            indicators_context (str): Calculated indicators context.

        Returns:
            str: Formatted context message.
        """

        return f"""
        DADOS DE MERCADO E FUNDAMENTOS (CVM Oficial + Yahoo Finance):
        Empresa: {company_name} (Ticker: {self.ticker})
        Preço Atual: R$ {current_price}
        
        1. Demonstrações Financeiras Brutas (Resumo):
        {str(financial_data)[:3000]}...
        
        {indicators_context}
        """

    def _execute_llm_analysis(self, messages: list) -> str:
        """Invokes the LLM and cleans the response.

        Args:
            messages (list): List of messages for the LLM.

        Returns:
            str: Cleaned LLM response content.
        """

        response = self.llm.invoke(messages)

        return cleanup_think_tags(response.content)

    def _parse_llm_response(self, content: str, valuation_metrics: str) -> AgentAnalysis:
        """Parses the LLM response content into structured AgentAnalysis.

        Args:
            content (str): LLM response content.
            valuation_metrics (str): Valuation data.

        Returns:
            AgentAnalysis: Structured analysis result.
        """

        try:
            # Clean markdown code blocks
            content = clean_json_markdown(content)

            data = json.loads(content)

            summary = data.get("summary", "Resumo indisponível.")
            details = data.get("details", "")
            if not details:
                details = str(data)

            metrics_objs = [
                FinancialMetric(
                    name=metric.get("name", "N/A"),
                    value=metric.get("value", 0),
                    unit=metric.get("unit", ""),
                    period=metric.get("period", ""),
                    description=metric.get("description", ""),
                )
                for metric in data.get("metrics", [])
            ]

            sources = ["CVM - Portal Dados Abertos", "Nexus Indicator Tools"]
            if "Mercado" in valuation_metrics:
                sources.append("B3")

            return AgentAnalysis(
                agent_name="Graham",
                ticker=self.ticker,
                summary=summary,
                details=details,
                metrics=metrics_objs,
                sources=sources,
                timestamp=datetime.now().isoformat(),
            )

        except (json.JSONDecodeError, AttributeError, TypeError, ValidationError) as error:
            return AgentAnalysis(
                agent_name="fundamentalist",
                ticker=self.ticker,
                summary="Erro na geração estruturada. Verifique logs.",
                details=f"O LLM não retornou JSON válido.\nConteúdo Bruto:\n{content}\nErro: {error}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

    def _extract_metadata(self, target_ticker: str, company_name: str) -> dict:
        """Extracts metadata about the company.

        Args:
            target_ticker (str): The target ticker.
            company_name (str): The company name.
        Returns:
            dict: Extracted metadata.
        """

        metadata = {}

        try:
            # CVM Data
            raw_profile = get_company_profile_data(target_ticker)
            if "error" not in raw_profile:
                metadata["company_name"] = raw_profile.get("company_name", company_name)
                metadata["activity"] = raw_profile.get("activity", "N/A")
            else:
                metadata["company_name"] = company_name

            # YFinance Data for Sector/Industry
            try:
                yf_symbol = ensure_sa_suffix(self.ticker)
                yf_ticker = yf.Ticker(yf_symbol)
                company_info = yf_ticker.info

                metadata["sector"] = company_info.get("sector", "N/A")
                if metadata.get("activity") == "N/A" or not metadata.get("activity"):
                    metadata["activity"] = company_info.get("industry", "N/A")
            except (RequestException, ValueError, IndexError, AttributeError) as error:
                logger.warning(f"YFinance metadata fetch failed for {self.ticker}: {error}")

        except (RequestException, ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            logger.error(f"Metadata extraction error: {error}")

        return metadata

    def analyze(self) -> dict:
        """Orchestrates the fundamental analysis process."""

        # 1. Identify Company
        company_name, search_term = self._identify_company()

        # 2. Fetch Core Data
        financial_data, current_price = self._fetch_market_data(company_name, search_term)

        # 3. Calculate Indicators
        target_ticker_for_tools = search_term
        indicators_context, val_data = self._calculate_indicators(target_ticker_for_tools, current_price)

        # 4. LLM Analysis
        system_prompt = self.prompt_manager.get('fundamentalist.agent.system_message')
        context_msg = self._prepare_llm_context(company_name, current_price, financial_data, indicators_context)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Gere a análise estruturada (JSON) para {self.ticker}:\n\n{context_msg}"),
        ]

        content = self._execute_llm_analysis(messages)

        # 5. Parse and Structure Result
        analysis = self._parse_llm_response(content, val_data)
        metadata = self._extract_metadata(target_ticker_for_tools, company_name)

        return {"analyses": [analysis], "metadata": metadata}


def fundamentalist_node(state: MarketAgentState):
    """Fundamentalist agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        AgentAnalysis: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = FundamentalistAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
