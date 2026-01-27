"""Quantitative Agent for performing technical analysis on companies using market data and LLMs."""

import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import ValidationError

from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings
from nexus_equitygraph.core.text_utils import clean_json_markdown, cleanup_think_tags
from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState
from nexus_equitygraph.tools.market_tools import get_stock_price_history


# pylint: disable=too-few-public-methods
class QuantitativeAgent:
    """Agent that performs technical analysis on companies using market data and LLMs."""

    def __init__(self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm=None) -> None:
        """Initialize the QuantitativeAgent.

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

    def _fetch_market_data(self) -> str:
        """Fetches market data (stock history).

        Returns:
            str: Market data string.
        """

        # Invokes Market Tool (yfinance)
        market_data = get_stock_price_history.invoke({"ticker": self.ticker})
        if "Erro" in str(market_data):
            logger.error(f"Erro ao buscar dados de mercado para {self.ticker}: {market_data}")
            return "Erro ao buscar dados de mercado."

        return market_data

    def _prepare_llm_context(self, market_data: str) -> str:
        """Formats the context message for the LLM.

        Args:
            market_data (str): Market data string.

        Returns:
            str: Formatted context message.
        """

        return f"Gere um relatório quantitativo (JSON) para {self.ticker} com base nestes dados:\n\n{market_data}"

    def _execute_llm_analysis(self, messages: list) -> str:
        """Invokes the LLM and cleans the response.

        Args:
            messages (list): List of messages for the LLM.

        Returns:
            str: Cleaned LLM response content.
        """

        response = self.llm.invoke(messages)

        return cleanup_think_tags(response.content)

    def _parse_llm_response(self, content: str) -> AgentAnalysis:
        """Parses the LLM response content into structured AgentAnalysis.

        Args:
            content (str): LLM response content.

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

            sources = ["Yahoo Finance", "Nexus Market Tools"]

            return AgentAnalysis(
                agent_name="Vector",
                ticker=self.ticker,
                summary=summary,
                details=details,
                metrics=metrics_objs,
                sources=sources,
                timestamp=datetime.now().isoformat(),
            )

        except (json.JSONDecodeError, AttributeError, TypeError, ValidationError) as error:
            return AgentAnalysis(
                agent_name="Vector",
                ticker=self.ticker,
                summary="Erro na geração estruturada. Verifique logs.",
                details=f"O LLM não retornou JSON válido.\nConteúdo Bruto:\n{content}\nErro: {error}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

    def analyze(self) -> dict:
        """Orchestrates the quantitative analysis process."""

        # 1. Fetch Data
        market_data = self._fetch_market_data()

        # 2. Prepare Context
        context_msg = self._prepare_llm_context(market_data)

        # 3. LLM Analysis
        # Using the prompt from the manager
        system_prompt = self.prompt_manager.get('quantitative.agent.system_message')

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_msg),
        ]

        content = self._execute_llm_analysis(messages)

        # 4. Parse and Structure Result
        analysis = self._parse_llm_response(content)

        return {"analyses": [analysis], "metadata": {}}


def quantitative_node(state: MarketAgentState):
    """Quantitative agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        dict: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = QuantitativeAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
