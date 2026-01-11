"""Configuration directories for Nexus EquityGraph using pathlib."""

from dataclasses import dataclass
from pathlib import Path


# Define the base directory four levels up from this file,
# which is the root of the project.
_BASE_DIRECTORY = Path(__file__).resolve().parent.parent.parent.parent


@dataclass(frozen=True)
class DirectoryConfigs:
    """Configuration directories using pathlib."""

    BASE_DIRECTORY: Path = _BASE_DIRECTORY
    DATA_DIRECTORY: Path = _BASE_DIRECTORY / "data"
    CVM_SUB_DIRECTORY: Path = DATA_DIRECTORY / "cvm"
    LOG_DIRECTORY: Path = DATA_DIRECTORY / "logs"
    NEWS_SUB_DIRECTORY: Path = DATA_DIRECTORY / "news"
