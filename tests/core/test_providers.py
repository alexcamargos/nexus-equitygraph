"""Tests for the LLM provider factory in nexus_equitygraph.core.providers module."""

import pytest

from nexus_equitygraph.core.providers import _get_groq_llm, _get_ollama_llm, create_llm_provider


class TestLLMProviderFactory:
    """Test suite for LLM provider factory logic."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Automatically clears LRU cache before each test to ensure isolation.

        Since the factory functions are cached, failing to clear them would cause
        tests to receive stale mocks or configurations from previous runs.
        """

        # Clear caches of the internal factory functions as well
        # to ensure complete isolation.
        create_llm_provider.cache_clear()
        _get_groq_llm.cache_clear()
        _get_ollama_llm.cache_clear()

    def test_create_ollama_provider_uses_settings(self, mocker):
        """Tests if Ollama provider is created with correct settings."""

        # Mock external class to avoid real connection attempts.
        mock_chat_ollama = mocker.patch("nexus_equitygraph.core.providers.ChatOllama")
        # Mock settings values to ensure we are testing the configuration flow.
        mocker.patch("nexus_equitygraph.core.providers.settings.ollama_base_url", "http://mock-url:11434")
        mocker.patch("nexus_equitygraph.core.providers.settings.ollama_default_model", "mock-llama3")

        # Action
        create_llm_provider(provider_name="ollama", temperature=0.7)

        # Assert: Verify if the class was instantiated with the correct parameters.
        mock_chat_ollama.assert_called_once_with(
            base_url="http://mock-url:11434",
            model="mock-llama3",
            temperature=0.7,
            reasoning=True,  # Hardcoded in providers.py
        )

    def test_create_groq_provider_uses_settings(self, mocker):
        """Tests if Groq provider is created with correct settings."""

        # Mock external class to avoid real connection attempts.
        mock_chat_groq = mocker.patch("nexus_equitygraph.core.providers.ChatGroq")
        # Mock settings values to ensure we are testing the configuration flow.
        mocker.patch("nexus_equitygraph.core.providers.settings.groq_default_model", "mock-llama3")
        mocker.patch("nexus_equitygraph.core.providers.settings.api_key", "mock-api-key")

        # Action
        create_llm_provider(provider_name="groq", temperature=0.1)

        # Assert: Verify if the class was instantiated with the correct parameters.
        mock_chat_groq.assert_called_once_with(model="mock-llama3", temperature=0.1, api_key="mock-api-key")

    def test_provider_override_model_name(self, mocker):
        """Tests if passing a specific model name overrides the default setting."""

        # Mock external class to avoid real connection attempts.
        mock_chat_ollama = mocker.patch("nexus_equitygraph.core.providers.ChatOllama")
        # Mock settings values to ensure we are testing the configuration flow.
        mocker.patch("nexus_equitygraph.core.providers.settings.ollama_default_model", "default-model")

        # Action
        create_llm_provider(provider_name="ollama", model_name="custom-model")

        # Assert: Verify if the class was instantiated with the overridden model name.
        assert mock_chat_ollama.call_args.kwargs['model'] == "custom-model"

    def test_unknown_provider_raises_error(self):
        """Tests if an invalid provider name raises ValueError."""

        with pytest.raises(ValueError, match="Unknown AI Provider"):
            create_llm_provider(provider_name="quantum_computer")

    def test_create_uses_default_provider_from_settings(self, mocker):
        """Tests if the factory uses the default provider from settings when none is specified."""

        mock_chat_groq = mocker.patch("nexus_equitygraph.core.providers.ChatGroq")

        # Mock settings to simulate Groq as default
        mocker.patch("nexus_equitygraph.core.providers.settings.provider", "groq")
        mocker.patch("nexus_equitygraph.core.providers.settings.api_key", "mock-key")
        mocker.patch("nexus_equitygraph.core.providers.settings.groq_default_model", "mock-model")

        # Action: Call without arguments to trigger default value logic
        create_llm_provider()

        # Assert: Verify if Groq provider was created.
        mock_chat_groq.assert_called_once()

    def test_caching_behavior(self, mocker):
        """Tests if the factory respects LRU cache (Singleton behavior for same args)."""

        # Mock external class to avoid real connection attempts.
        mocker.patch("nexus_equitygraph.core.providers.ChatOllama")
        # Mock settings values to ensure we are testing the configuration flow.
        mocker.patch("nexus_equitygraph.core.providers.settings.ollama_base_url", "http://mock")
        mocker.patch("nexus_equitygraph.core.providers.settings.ollama_default_model", "mock")

        # Action
        instance_1 = create_llm_provider("ollama")
        instance_2 = create_llm_provider("ollama")

        # Assert: Both variables should point to the exact same object in memory
        assert instance_1 is instance_2
