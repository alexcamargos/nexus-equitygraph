"""Risk Manager Agent for analyzing macro and micro risks."""

from datetime import datetime
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

# from pydantic import ValidationError # Removed unused

from nexus_equitygraph.agents.base import BaseAgent
from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.domain.schemas import AnalysisOutput
from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState


# pylint: disable=too-few-public-methods
class RiskManagerAgent(BaseAgent):
    """Agent that analyzes macro and micro factors that may threaten the asset."""

    def __init__(
        self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm: Optional[BaseChatModel] = None
    ) -> None:
        """Initialize the RiskManagerAgent.

        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseChatModel]): The language model to use. If None, a default will be created.
        """

        # Initialize BaseAgent with AnalysisOutput schema for structured output parsing.
        super().__init__(state, prompt_manager, llm, output_schema=AnalysisOutput)

    def _prepare_llm_context(self) -> str:
        """Formats the context message for the LLM.

        Returns:
            str: Formatted context message.
        """

        return f"Avalie os riscos associados ao investimento em {self.ticker}."

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

        sources = output.sources or ["Model Knowledge Base"]

        return AgentAnalysis(
            agent_name="Sentry",
            ticker=self.ticker,
            summary=output.summary,
            details=output.details,
            metrics=metrics_objs,
            sources=sources,
            timestamp=datetime.now().isoformat(),
        )

    def analyze(self) -> dict:
        """Orchestrates the risk analysis process.

        Returns:
            dict: The analysis result containing analyses and metadata.
        """

        # 1. Prepare Context
        context_msg = self._prepare_llm_context()

        # 2. LLM Analysis
        system_prompt = self.prompt_manager.get('risk_manager.agent.system_message')

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_msg),
        ]

        # Use BaseAgent execution which now returns structured AnalysisOutput.
        try:
            structured_output = self._execute_llm_analysis(messages)
            analysis = self._create_agent_analysis(structured_output)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error in RiskManager Agent analysis: {e}")
            analysis = AgentAnalysis(
                agent_name="Sentry",
                ticker=self.ticker,
                summary="Erro na geração da análise.",
                details=f"Ocorreu um erro ao processar a análise de riscos: {str(e)}",
                metrics=[],
                sources=["Error"],
                timestamp=datetime.now().isoformat(),
            )

        return {"analyses": [analysis]}


def risk_manager_node(state: MarketAgentState):
    """Risk Manager agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        dict: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = RiskManagerAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
