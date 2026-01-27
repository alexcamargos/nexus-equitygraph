"""Reviewer Agent for validating analysis reports."""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import ValidationError

from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings
from nexus_equitygraph.core.text_utils import clean_json_markdown, cleanup_think_tags
from nexus_equitygraph.domain.state import MarketAgentState, ReviewFeedback


# pylint: disable=too-few-public-methods
class ReviewerAgent:
    """Agent that reviews the reports produced by other analysts."""

    def __init__(self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm=None) -> None:
        """Initialize the ReviewerAgent.

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

    def _execute_llm_analysis(self, messages: list) -> str:
        """Invokes the LLM and cleans the response.

        Args:
            messages (list): List of messages for the LLM.

        Returns:
            str: Cleaned LLM response content.
        """

        response = self.llm.invoke(messages)

        return cleanup_think_tags(response.content)

    def _parse_llm_response(self, content: str) -> ReviewFeedback:
        """Parses the LLM response content into structured ReviewFeedback.

        Args:
            content (str): LLM response content.

        Returns:
            ReviewFeedback: Structured feedback.
        """

        try:
            # Clean markdown code blocks
            content = clean_json_markdown(content)

            data = json.loads(content)
            if "agent_name" not in data:
                data["agent_name"] = "Reviewer"

            return ReviewFeedback(**data)

        except (json.JSONDecodeError, AttributeError, TypeError, ValidationError) as error:
            logger.error(f"Erro no JSON Parsing do Reviewer: {error}. Conteúdo: {content[:100]}...")
            # Fallback
            return ReviewFeedback(
                agent_name="Reviewer",
                approved=True,
                comments=["Aprovação forçada por erro de parser JSON local."],
                recommendations=[],
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

        content = self._execute_llm_analysis(messages)

        # 3. Parse and Structure Result
        feedback = self._parse_llm_response(content)

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
