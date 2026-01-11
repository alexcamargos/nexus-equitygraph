"""Module to create and configure LLM providers based on settings."""

from functools import lru_cache
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from .settings import settings


@lru_cache
def _get_groq_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> BaseChatModel:
    """Factory to retrieve a Groq LLM instance.

    Args:
        model_name (Optional[str]): Specific model to use.
                                    Defaults to settings.groq_default_model.
        temperature (float): Sampling temperature.
                             Defaults to 0.0.

    Returns:
        BaseChatModel: Configured ChatGroq instance.
    """

    # Determine the model to use, falling back to settings if not provided.
    model = model_name or settings.groq_default_model

    return ChatGroq(model=model, temperature=temperature, api_key=settings.api_key)


@lru_cache
def _get_ollama_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> BaseChatModel:
    """Factory to retrieve an Ollama LLM instance (Local).

    Args:
        model_name (Optional[str]): Specific model to use.
                                    Defaults to settings.ollama_default_model.
        temperature (float): Sampling temperature.
                             Defaults to 0.0.

    Returns:
        BaseChatModel: Configured ChatOllama instance.
    """

    # Determine the model to use, falling back to settings if not provided.
    model = model_name or settings.ollama_default_model

    return ChatOllama(base_url=settings.ollama_base_url, model=model, temperature=temperature, reasoning=True)


@lru_cache
def create_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """Factory to create an LLM provider based on the configuration.

    Args:
        provider_name (Optional[str]): Name of the AI provider.
                                       Defaults to settings.provider if None.
        model_name (Optional[str]): Specific model to use.
        temperature (float): Sampling temperature.

    Returns:
        BaseChatModel: Configured LLM provider instance.
    """

    # Determine the actual provider to use, falling back to settings if not provided.
    actual_provider = provider_name or settings.provider

    match actual_provider.lower():
        case "groq":
            return _get_groq_llm(temperature=temperature, model_name=model_name)
        case "ollama":
            return _get_ollama_llm(temperature=temperature, model_name=model_name)
        case _:
            raise ValueError(f"Unknown AI Provider: {actual_provider}")


__all__ = ["create_llm_provider"]
