"""Supervisor Agent for aggregating analyses and generating final report."""

from langchain_core.messages import HumanMessage, SystemMessage

from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol, get_prompt_manager
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings
from nexus_equitygraph.core.text_utils import cleanup_think_tags
from nexus_equitygraph.domain.state import MarketAgentState


# pylint: disable=too-few-public-methods
class SupervisorAgent:
    """Agent that consolidates all analyses into a final investment recommendation."""

    def __init__(self, state: MarketAgentState, prompt_manager: PromptManagerProtocol, llm=None) -> None:
        """Initialize the SupervisorAgent.

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
        self.feedback = state.feedback

    def _prepare_llm_context(self) -> str:
        """Formats the context message for the LLM.

        Returns:
            str: Formatted context message.
        """

        feedback_text = self.feedback.comments if self.feedback else 'N/A'
        context_text = f"Feedback do Revisor: {feedback_text}\n"

        for analysis in self.analyses:
            context_text += f"\n--- Relatório de {analysis.agent_name} ---\n{analysis.details}\n"

        return f"Consolide o relatório final para {self.ticker} com base nestes dados (Responda em Português do Brasil):\n{context_text}"

    def _execute_llm_analysis(self, messages: list) -> str:
        """Invokes the LLM and cleans the response.

        Args:
            messages (list): List of messages for the LLM.

        Returns:
            str: Cleaned LLM response content.
        """

        response = self.llm.invoke(messages)

        if isinstance(response, dict):
            return cleanup_think_tags(response.get("content", ""))

        # JSON Fallback
        content = getattr(response, "content", "")

        return cleanup_think_tags(str(content))

    def analyze(self) -> dict:
        """Orchestrates the report generation process.

        Returns:
            dict: The final report.
        """

        # 1. Prepare Context
        context_msg = self._prepare_llm_context()

        # 2. LLM Analysis
        system_prompt = self.prompt_manager.get('supervisor.agent.system_message')

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_msg),
        ]

        content = self._execute_llm_analysis(messages)

        return {"final_report": content}


def supervisor_node(state: MarketAgentState):
    """Supervisor agent node function.

    Args:
        state (MarketAgentState): The market agent state.

    Returns:
        dict: The analysis result.
    """

    prompt_handler = get_prompt_manager()
    agent = SupervisorAgent(state, prompt_manager=prompt_handler)

    return agent.analyze()
