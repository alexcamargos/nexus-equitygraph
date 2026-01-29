"""Quantitative Agent for performing technical analysis on companies using market data and LLMs."""

from datetime import datetime
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from nexus_equitygraph.agents.base import BaseAgent
from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.domain.schemas import AnalysisOutput
from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState
from nexus_equitygraph.tools.market_tools import get_stock_price_history


# pylint: disable=too-few-public-methods
class QuantitativeAgent(BaseAgent):
    """Agent that performs technical analysis on companies using market data and LLMs."""

    def __init__(
        self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm: Optional[BaseChatModel] = None
    ) -> None:
        """Initialize the QuantitativeAgent.

        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseChatModel]): The language model to use. If None, a default will be created.
        """

        # Initialize BaseAgent with AnalysisOutput schema for structured output parsing.
        super().__init__(state, prompt_manager, llm, output_schema=AnalysisOutput)

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

        return f"Gere um relatório quantitativo para {self.ticker} com base nestes dados:\n\n{market_data}"

    def _create_agent_analysis(self, output: AnalysisOutput) -> AgentAnalysis:
        """Converts structured LLM output to AgentAnalysis state object.

        Args:
            output (AnalysisOutput): Structured output from LLM.

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

        sources = output.sources or ["Yahoo Finance", "Nexus Market Tools"]

        return AgentAnalysis(
            agent_name="Vector",
            ticker=self.ticker,
            summary=output.summary,
            details=output.details,
            metrics=metrics_objs,
            sources=sources,
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

        # Use BaseAgent execution which now returns structured AnalysisOutput.
        try:
            structured_output = self._execute_llm_analysis(messages)
            analysis = self._create_agent_analysis(structured_output)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error in Quantitative Agent analysis: {e}")
            analysis = AgentAnalysis(
                agent_name="Vector",
                ticker=self.ticker,
                summary="Erro na geração da análise.",
                details=f"Ocorreu um erro ao processar a análise quantitativa: {str(e)}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

        return {"analyses": [analysis]}


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
