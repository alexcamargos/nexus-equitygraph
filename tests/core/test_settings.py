"""Tests for the application configuration in nexus_equitygraph.core.settings module."""

import pytest
from pydantic import SecretStr, ValidationError

from nexus_equitygraph.core.settings import NexusEquityGraphSettings


class TestNexusEquityGraphSettings:
    """Test suite for application configuration validation."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Fixture that simulates a loaded .env file.

        Defines a consistent base state for tests, avoiding code repetition.
        """
        # Setup: Define environment variables simulating a .env file
        env_vars = {
            "AI_PROVIDER": "ollama",
            "AI_API_KEY": "test-secret-key",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_DEFAULT_MODEL": "llama3-8b",
            "GROQ_DEFAULT_MODEL": "llama3-16b",
            "LANGCHAIN_TRACING_V2": "True",
            "LANGCHAIN_ENDPOINT": "https://api.smith.langchain.com",
            "LANGCHAIN_PROJECT": "nexus-equitygraph-test",
            "LANGCHAIN_API_KEY": "ls__test_key",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        return monkeypatch

    @pytest.fixture
    def settings_factory(self):
        """Fixture that returns a factory to create settings ignoring the local .env."""

        def _create():
            """Creates a NexusEquityGraphSettings instance without loading .env."""

            return NexusEquityGraphSettings(_env_file=None)

        return _create

    def test_load_settings_from_env_vars(self, mock_env, settings_factory):
        """Tests if settings are correctly loaded from environment variables."""

        # Action
        settings = settings_factory()

        # Assert
        assert settings.provider == "ollama"
        assert settings.api_key is not None
        assert settings.api_key.get_secret_value() == "test-secret-key"
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_default_model == "llama3-8b"

    def test_default_provider_when_env_not_set(self, mock_env, settings_factory):
        """Tests if provider uses default value when AI_PROVIDER is not set."""

        # Setup: Remove the variable defined by the fixture.
        mock_env.delenv("AI_PROVIDER", raising=False)

        # Action
        settings = settings_factory()

        # Assert: Should use default value instead of raising error
        assert settings.provider == "ollama"

    def test_default_values_for_optional_fields(self, mock_env, settings_factory):
        """Tests if optional fields assume correct default values (None or False)."""

        # Remove variables defined in conftest that we want to test as defaults (None/False)
        mock_env.delenv("LANGCHAIN_TRACING_V2", raising=False)
        mock_env.delenv("AI_API_KEY", raising=False)
        mock_env.setenv("AI_PROVIDER", "groq")

        settings = settings_factory()

        assert settings.provider == "groq"
        assert settings.api_key is None
        assert settings.azure_endpoint is None
        assert settings.langchain_tracing_v2 is False

    def test_alias_mapping_works(self, mock_env, settings_factory):
        """Tests if aliases (validation_alias) correctly map env vars."""
        # The field in the class is 'provider', but the env var is 'AI_PROVIDER'
        mock_env.setenv("AI_PROVIDER", "openai")

        settings = settings_factory()

        assert settings.provider == "openai"
        assert settings.langchain_tracing_v2 is True

    def test_sensitive_fields_are_defined_as_secrets(self, mock_env, settings_factory):
        """Tests if sensitive fields are correctly typed as SecretStr to prevent leaks."""

        settings = settings_factory()

        # Verify that the fields are indeed SecretStr instances
        assert isinstance(settings.api_key, SecretStr)
        assert isinstance(settings.langchain_api_key, SecretStr)

        # Verify that the string representation is masked (regression test for security)
        assert str(settings.api_key) == "**********"
        assert str(settings.langchain_api_key) == "**********"

    def test_get_settings_singleton_behavior(self, mock_env):
        """Tests if the application's _get_settings function respects the cache (Singleton)."""
        # Local import to access internal function (not exposed in __init__)
        from nexus_equitygraph.core.settings import _get_settings

        # Clears the cache to ensure we are testing a new creation
        _get_settings.cache_clear()

        instance_1 = _get_settings()
        instance_2 = _get_settings()

        assert instance_1 is instance_2
