"""Application configuration for Nexus EquityGraph."""

from functools import lru_cache
from typing import Annotated, List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .configs import DirectoryConfigs as Cfg


class BaseAppSettings(BaseSettings):
    """Base configuration with common settings for .env loading."""

    model_config = SettingsConfigDict(env_file=Cfg.BASE_DIRECTORY / ".env", env_file_encoding="utf-8", extra="ignore")


class CVMSettings(BaseAppSettings):
    """Configuration for CVM (Comissão de Valores Mobiliários) API."""

    # CVM Base URLs for different data endpoints.
    base_url_itr: str = Field(default=..., validation_alias="CVM_BASE_URL_ITR")
    base_url_cad: str = Field(default=..., validation_alias="CVM_BASE_URL_CAD")
    base_url_dfp: str = Field(default=..., validation_alias="CVM_BASE_URL_DFP")

    # CVM Report Types to be fetched.
    report_types: List[str] = Field(
        default=["BPA", "BPP", "DRE", "DFC_MD", "DFC_MI", "DMPL", "DRA", "DVA", "composicao_capital", "parecer"],
        validation_alias="CVM_REPORT_TYPES",
    )


class NexusEquityGraphSettings(BaseAppSettings):
    """Application settings for Nexus EquityGraph."""

    # AI Provider Configuration
    provider: Annotated[str, Field(validation_alias="AI_PROVIDER")] = "ollama"
    # AI API Key (Common for all providers)
    api_key: Optional[SecretStr] = Field(default=None, validation_alias="AI_API_KEY")

    # Ollama Configuration
    ollama_base_url: Optional[str] = Field(default=None, validation_alias="OLLAMA_BASE_URL")
    ollama_default_model: Optional[str] = Field(default=None, validation_alias="OLLAMA_DEFAULT_MODEL")

    # Groq Configuration
    groq_default_model: Optional[str] = Field(default=None, validation_alias="GROQ_DEFAULT_MODEL")

    # Azure Configuration
    azure_endpoint: Optional[str] = Field(default=None, validation_alias="AZURE_ENDPOINT")
    azure_api_version: Optional[str] = Field(default=None, validation_alias="AZURE_API_VERSION")
    azure_deployment_name: Optional[str] = Field(default=None, validation_alias="AZURE_DEPLOYMENT_NAME")

    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(default=False, validation_alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: Optional[str] = Field(default=None, validation_alias="LANGCHAIN_ENDPOINT")
    langchain_project: Optional[str] = Field(default=None, validation_alias="LANGCHAIN_PROJECT")
    langchain_api_key: Optional[SecretStr] = Field(default=None, validation_alias="LANGCHAIN_API_KEY")


@lru_cache(maxsize=1)
def _get_settings() -> NexusEquityGraphSettings:
    """Retrieve cached application settings."""

    return NexusEquityGraphSettings()


@lru_cache(maxsize=1)
def _get_cvm_settings() -> CVMSettings:
    """Retrieve cached CVM settings."""

    return CVMSettings()


settings = _get_settings()
cvm_settings = _get_cvm_settings()

__all__ = ["settings", "cvm_settings"]
