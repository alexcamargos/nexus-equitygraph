"""Base Agent for Nexus EquityGraph agents."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings
from nexus_equitygraph.core.text_utils import clean_json_markdown, cleanup_think_tags
from nexus_equitygraph.domain.state import MarketAgentState


# pylint: disable=too-few-public-methods
class BaseAgent(ABC):
    """Abstract base class for all specialist agents."""

    def __init__(
        self,
        state: MarketAgentState,
        prompt_manager: PromptManagerProtocol,
        llm: Optional[BaseChatModel] = None,
    ) -> None:
        """Initialize the BaseAgent.

        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseChatModel]): The language model to use. If None, a default will be created.
        """

        self.state = state
        self.prompt_manager = prompt_manager
        self.ticker = state.ticker

        # Default model configuration: reasoning model or default model, temperature 0 for deterministic output.
        model_name = settings.ollama_model_reasoning or settings.ollama_default_model
        self.llm = llm or create_llm_provider(temperature=0, model_name=model_name)

    def _execute_llm_analysis(self, messages: List[Any]) -> str:
        """Invokes the LLM and cleans the response.

        Args:
            messages (list): List of messages for the LLM.

        Returns:
            str: Cleaned LLM response content (think tags removed).
        """

        response = self.llm.invoke(messages)

        return cleanup_think_tags(response.content)

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        """Safely parses a JSON string (possibly wrapped in markdown) into a dictionary.

        Args:
            content (str): The raw string content from the LLM.

        Returns:
            Dict[str, Any]: The parsed JSON dictionary.

        Raises:
            json.JSONDecodeError: If parsing fails.
        """

        cleaned_content = clean_json_markdown(content)

        return json.loads(cleaned_content)

    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """Orchestrates the analysis process. Must be implemented by subclasses.

        Returns:
            Dict[str, Any]: The analysis state update.
        """
