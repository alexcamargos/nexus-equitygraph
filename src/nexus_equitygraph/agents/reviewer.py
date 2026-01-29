"""Reviewer Agent for validating analysis reports."""

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

# from pydantic import ValidationError # Removed unused

from nexus_equitygraph.agents.base import BaseAgent
from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.domain.schemas import ReviewerOutput
from nexus_equitygraph.domain.state import MarketAgentState, ReviewFeedback


# pylint: disable=too-few-public-methods
class ReviewerAgent(BaseAgent):
    """Agent that reviews the reports produced by other analysts."""

    def __init__(
        self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm: Optional[BaseChatModel] = None
    ) -> None:
        """Initialize the ReviewerAgent.

        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseChatModel]): The language model to use. If None, a default will be created.
        """

        # Initialize BaseAgent with AnalysisOutput schema for structured output parsing.
        super().__init__(state, prompt_manager, llm, output_schema=ReviewerOutput)

        # Store execution-specific properties
        self.analyses = state.analyses
        self.iteration = state.iteration

    def _prepare_llm_context(self) -> str:
        """Formats the context message for the LLM.

        Returns:
            str: Formatted context message.
        """

        context_text = ""
        for index, analysis in enumerate(self.analyses):
            context_text += f"\n--- Análise {index+1} ({analysis.agent_name}) ---\n"
            context_text += f"Resumo: {analysis.summary}\n"
            context_text += f"Fontes: {analysis.sources}\n"
            # Limiting detail length to avoid context overflow if many agents.
            context_text += f"Detalhes: {analysis.details[:2000]}...\n"

        return f"Revise estas análises para o ativo {self.ticker} (Iteração {self.iteration}):\n{context_text}"

    def _create_review_feedback(self, output: ReviewerOutput) -> ReviewFeedback:
        """Converts structured LLM output to ReviewFeedback state object.

        Args:
            output (ReviewerOutput): Structured output from LLM.

        Returns:
            ReviewFeedback: Structured feedback.
        """

        return ReviewFeedback(
            agent_name="Reviewer",
            approved=output.approved,
            comments=output.comments,
            recommendations=output.recommendations,
        )

    def analyze(self) -> dict:
        """Orchestrates the review process.

        Returns:
            dict: The feedback result.
        """

        # 1. Prepare Context
        context_msg = self._prepare_llm_context()

        # 2. LLM Analysis
        system_prompt = self.prompt_manager.get('reviewer.agent.system_message')

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_msg),
        ]

        # Use BaseAgent execution which now returns structured ReviewerOutput
        try:
            structured_output = self._execute_llm_analysis(messages)
            feedback = self._create_review_feedback(structured_output)
        except Exception as error:  # pylint: disable=broad-except
            logger.error(f"Error in Reviewer Agent analysis: {error}")
            feedback = ReviewFeedback(
                agent_name="Reviewer",
                approved=False,  # Safe default on error
                comments=[f"Erro crítico durante a revisão: {str(error)}"],
                recommendations=[],
            )

        return {"feedback": feedback}


def reviewer_node(state: MarketAgentState):
    """Reviewer agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        dict: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = ReviewerAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
