"""Base Agent for Nexus EquityGraph agents."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from nexus_equitygraph.core.prompt_manager import PromptManagerProtocol
from nexus_equitygraph.core.providers import create_llm_provider
from nexus_equitygraph.core.settings import settings
from nexus_equitygraph.core.text_utils import cleanup_think_tags
from nexus_equitygraph.domain.state import MarketAgentState


# pylint: disable=too-few-public-methods
class BaseAgent(ABC):
    """Abstract base class for all specialist agents."""

    def __init__(
        self,
        state: MarketAgentState,
        prompt_manager: PromptManagerProtocol,
        llm: Optional[BaseChatModel] = None,
        output_schema: Optional[type[BaseModel]] = None,
    ) -> None:
        """Initialize the BaseAgent.

        Args:
            state (MarketAgentState): The market agent state.
            prompt_manager (PromptManagerProtocol): The prompt manager.
            llm (Optional[BaseChatModel]): The language model to use. If None, a default will be created.
            output_schema (Optional[type[BaseModel]]): Pydantic model for structured output.
        """

        self.state = state
        self.prompt_manager = prompt_manager
        self.ticker = state.ticker
        self.output_schema = output_schema

        # Default model configuration: reasoning model or default model, temperature 0 for deterministic output.
        model_name = settings.ollama_model_reasoning or settings.ollama_default_model

        base_llm = llm or create_llm_provider(temperature=0, model_name=model_name)

        # If schema is provided, bind it immediately
        if self.output_schema:
            self.llm = base_llm.with_structured_output(self.output_schema)
        else:
            self.llm = base_llm

    def _execute_llm_analysis(self, messages: List[Any]) -> Any:
        """Invokes the LLM.

        Args:
            messages (list): List of messages for the LLM.

        Returns:
            Any: The structured response (if schema provided) or cleaned string (if not).
        """

        response = self.llm.invoke(messages)

        # If we have a schema, response is already a Pydantic object
        # (or dict depending on backend); return as is.
        if self.output_schema:
            return response

        # Legacy/String Fallback
        if isinstance(response, dict):
            return cleanup_think_tags(response.get("content", ""))

        # JSON Fallback
        content = getattr(response, "content", "")

        return cleanup_think_tags(str(content))

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        """Safely parses JSON content from LLM response.

        Args:
            content (str): The LLM response content.

        Returns:
            Dict[str, Any]: The parsed JSON object.

        Raises:
            json.JSONDecodeError: If the content cannot be parsed as JSON.
        """

        cleaned = content.strip()

        # Handle markdown code blocks
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: try to find the first '{' and last '}'
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                return json.loads(cleaned[start : end + 1])
            raise

    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """Orchestrates the analysis process. Must be implemented by subclasses.

        Returns:
            Dict[str, Any]: The analysis state update.
        """
