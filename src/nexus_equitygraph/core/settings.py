"""Application configuration for Nexus EquityGraph."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .configs import DirectoryConfigs as Cfg


class BaseAppSettings(BaseSettings):
    """Base configuration with common settings for .env loading."""

    model_config = SettingsConfigDict(
        env_file=Cfg.BASE_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CVMSettings(BaseAppSettings):
    """Configuration for CVM (Comissão de Valores Mobiliários) API."""

    base_url_itr: Annotated[str, Field(validation_alias="CVM_BASE_URL_ITR")]
    base_url_cad: Annotated[str, Field(validation_alias="CVM_BASE_URL_CAD")]
    base_url_dfp: Annotated[str, Field(validation_alias="CVM_BASE_URL_DFP")]

    report_types: Annotated[
        list[str],
        Field(validation_alias="CVM_REPORT_TYPES"),
    ] = ["BPA", "BPP", "DRE", "DFC_MD", "DFC_MI", "DMPL", "DRA", "DVA", "composicao_capital", "parecer"]


class NexusEquityGraphSettings(BaseAppSettings):
    """Application settings for Nexus EquityGraph."""

    # AI Provider Configuration
    provider: Annotated[str, Field(validation_alias="AI_PROVIDER")] = "ollama"
    api_key: Annotated[SecretStr | None, Field(validation_alias="AI_API_KEY")] = None

    # Ollama Configuration
    ollama_base_url: Annotated[str | None, Field(validation_alias="OLLAMA_BASE_URL")] = None
    ollama_default_model: Annotated[str | None, Field(validation_alias="OLLAMA_DEFAULT_MODEL")] = None

    # Groq Configuration
    groq_default_model: Annotated[str | None, Field(validation_alias="GROQ_DEFAULT_MODEL")] = None

    # Azure Configuration
    azure_endpoint: Annotated[str | None, Field(validation_alias="AZURE_ENDPOINT")] = None
    azure_api_version: Annotated[str | None, Field(validation_alias="AZURE_API_VERSION")] = None
    azure_deployment_name: Annotated[str | None, Field(validation_alias="AZURE_DEPLOYMENT_NAME")] = None

    # LangSmith Configuration
    langchain_tracing_v2: Annotated[bool, Field(validation_alias="LANGCHAIN_TRACING_V2")] = False
    langchain_endpoint: Annotated[str | None, Field(validation_alias="LANGCHAIN_ENDPOINT")] = None
    langchain_project: Annotated[str | None, Field(validation_alias="LANGCHAIN_PROJECT")] = None
    langchain_api_key: Annotated[SecretStr | None, Field(validation_alias="LANGCHAIN_API_KEY")] = None


@lru_cache(maxsize=1)
def _get_settings() -> NexusEquityGraphSettings:
    """Retrieve cached application settings."""

    return NexusEquityGraphSettings()


@lru_cache(maxsize=1)
def _get_cvm_settings() -> CVMSettings:
    """Retrieve cached CVM settings."""

    return CVMSettings()  # type: ignore[call-arg]


settings = _get_settings()
cvm_settings = _get_cvm_settings()

__all__ = ["settings", "cvm_settings"]
