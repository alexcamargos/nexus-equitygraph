"""Fundamentalist Agent for performing fundamental analysis on companies using financial statements and LLMs."""

from datetime import datetime
from typing import Optional

import yfinance as yf
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from requests import RequestException

from nexus_equitygraph.agents.base import BaseAgent
from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.domain.schemas import AnalysisOutput
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


# pylint: disable=too-few-public-methods
class FundamentalistAgent(BaseAgent):
    """Agent that performs fundamental analysis on companies using financial statements and LLMs."""

    def __init__(
        self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm: Optional[BaseChatModel] = None
    ) -> None:
        """Initialize the FundamentalistAgent.

        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseChatModel]): The language model to use. If None, a default will be created.
        """

        # Initialize BaseAgent with AnalysisOutput schema for structured output parsing.
        super().__init__(state, prompt_manager, llm, output_schema=AnalysisOutput)

    def _identify_company(self) -> tuple[str, str]:
        """Resolves company name and search term.

        Returns:
            tuple[str, str]: Company name and search term.
        """

        company_name = get_company_name_from_ticker.invoke({"ticker": self.ticker})

        # Check for valid name. If invalid, fallback to ticker as search term.
        is_invalid_name = not company_name or "nome não disponível" in company_name.lower()

        # If name is not available, we use ticker for search.
        if is_invalid_name:
            company_name = self.ticker
            search_term = self.ticker
        else:
            search_term = ensure_sa_suffix(company_name)

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

    def _create_agent_analysis(self, output: AnalysisOutput, valuation_metrics: str) -> AgentAnalysis:
        """Converts structured LLM output to AgentAnalysis state object.

        Args:
            output (AnalysisOutput): Structured output from LLM.
            valuation_metrics (str): Valuation data context.

        Returns:
            AgentAnalysis: Structured analysis result.
        """
        metrics_objs = []
        for metric in output.metrics:
            metrics_objs.append(
                FinancialMetric(
                    name=metric.name,
                    value=metric.value,
                    unit=metric.unit or "",
                    period=metric.period or "",
                    description=metric.description or "",
                )
            )

        sources = output.sources or ["CVM - Portal Dados Abertos", "Nexus Indicator Tools"]
        if "Mercado" in valuation_metrics and "B3" not in sources:
            sources.append("B3")

        return AgentAnalysis(
            agent_name="Graham",
            ticker=self.ticker,
            summary=output.summary,
            details=output.details,
            metrics=metrics_objs,
            sources=sources,
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
            HumanMessage(content=f"Gere a análise estruturada para {self.ticker}:\n\n{context_msg}"),
        ]

        # Use BaseAgent excecution which now returns structured AnalysisOutput
        try:
            structured_output = self._execute_llm_analysis(messages)
            analysis = self._create_agent_analysis(structured_output, val_data)
        except Exception as e:
            logger.error(f"Error in Fundamentalist Agent analysis: {e}")
            analysis = AgentAnalysis(
                agent_name="Graham",
                ticker=self.ticker,
                summary="Erro na geração da análise.",
                details=f"Ocorreu um erro ao processar a análise fundamentalista: {str(e)}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

        # 5. Extract Metadata
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
