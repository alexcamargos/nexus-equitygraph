"""Application configuration for Nexus EquityGraph."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .configs import DirectoryConfigs as Cfg


class NexusEquityGraphSettings(BaseSettings):
    """Application settings for Nexus EquityGraph."""

    # AI Provider Configuration
    provider: str = Field(..., validation_alias="AI_PROVIDER")
    # AI API Key (Common for all providers)
    api_key: Optional[SecretStr] = Field(None, validation_alias="AI_API_KEY")

    # Ollama Configuration
    ollama_base_url: Optional[str] = Field(None, validation_alias="OLLAMA_BASE_URL")
    ollama_default_model: Optional[str] = Field(None, validation_alias="OLLAMA_DEFAULT_MODEL")

    # Groq Configuration
    groq_default_model: Optional[str] = Field(None, validation_alias="GROQ_DEFAULT_MODEL")

    # Azure Configuration
    azure_endpoint: Optional[str] = Field(None, validation_alias="AZURE_ENDPOINT")
    azure_api_version: Optional[str] = Field(None, validation_alias="AZURE_API_VERSION")
    azure_deployment_name: Optional[str] = Field(None, validation_alias="AZURE_DEPLOYMENT_NAME")

    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(False, validation_alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: Optional[str] = Field(None, validation_alias="LANGCHAIN_ENDPOINT")
    langchain_project: Optional[str] = Field(None, validation_alias="LANGCHAIN_PROJECT")
    langchain_api_key: Optional[SecretStr] = Field(None, validation_alias="LANGCHAIN_API_KEY")

    model_config = SettingsConfigDict(
        env_file=Cfg.BASE_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache(maxsize=1)
def _get_settings() -> NexusEquityGraphSettings:
    """Retrieve cached application settings."""

    return NexusEquityGraphSettings()

settings = _get_settings()

__all__ = ["settings"]
