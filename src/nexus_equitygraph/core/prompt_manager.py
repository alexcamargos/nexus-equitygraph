"""Centralized Prompt Manager for Nexus EquityGraph."""

import operator
import threading
import tomllib
from functools import lru_cache, reduce
from pathlib import Path
from typing import Any, Dict, Protocol, Union

from loguru import logger
from pydantic import RootModel, ValidationError

from nexus_equitygraph.core.configs import DirectoryConfigs as Cfg
from nexus_equitygraph.core.exceptions import PromptError, PromptNotFoundError


class PromptSchema(RootModel):
    """Schema for validating prompt data loaded from TOML."""

    root: Dict[str, Union[str, int, float, bool, list, dict]]


# pylint: disable=unnecessary-ellipsis
class PromptManagerProtocol(Protocol):
    """Protocol defining the interface for prompt retrieval."""

    def clear_cache(self) -> None:
        """Clears the internal prompt cache."""
        ...

    def get(self, path: str) -> str:
        """Retrieves a prompt using dot notation."""
        ...


class PromptManager:
    """Centralized system prompt manager.

    Implements Lazy Loading: loads TOML files on demand (only when requested),
    avoiding memory waste and I/O at startup.
    """

    def __init__(self, prompts_dir: Path = Cfg.PROMPTS_DIR) -> None:
        """Initialize the PromptManager with a thread-safe cache.

        Args:
            prompts_dir (Path): Directory containing prompt TOML files.
        """

        self.prompts_dir = prompts_dir

        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()

    def _load_file(self, namespace: str) -> None:
        """Loads a specific TOML file into the cache, if it exists.

        Args:
            namespace (str): TOML file name (without extension).
        """

        with self._lock:
            if namespace in self._cache:
                return

            toml_path = self.prompts_dir / f'{namespace}.toml'

            # If the prompt file does not exist, cache as empty to avoid repeated reads.
            if not toml_path.exists():
                logger.error(f'Prompt file not found: {toml_path}')
                self._cache[namespace] = {}

                return

            try:
                with open(toml_path, 'rb') as file:
                    data = tomllib.load(file)

                    # Validate data using Pydantic.
                    self._cache[namespace] = PromptSchema(root=data).root

                    logger.debug(f'Prompt loaded: {namespace}.toml')
            except tomllib.TOMLDecodeError as error:
                logger.error(f'Syntax error in TOML file {namespace}.toml: {error}')
                self._cache[namespace] = {}
            except ValidationError as error:
                logger.error(f'Validation error in {namespace}.toml: {error}')
                self._cache[namespace] = {}
            except OSError as error:
                logger.error(f'I/O error reading {namespace}.toml: {error}')
                self._cache[namespace] = {}

    def clear_cache(self) -> None:
        """Clears the internal prompt cache to force reloading from disk."""

        with self._lock:
            self._cache.clear()
            logger.debug("Prompt cache cleared.")

    def get(self, path: str) -> str:
        """Retrieves a prompt using dot notation (file.section.key).

        Loads the corresponding TOML file on demand (lazy loading).

        Args:
            path (str): Prompt path in 'file.key' format.
                        Example: 'agent.slm.system_message'
                        (Reads 'agent.toml' -> section [slm] -> key 'system_message')

        Returns:
            str: The prompt text or empty string if it fails.
        """

        keys = path.split('.')
        if len(keys) < 2:
            raise PromptError(f"Invalid prompt path (requires 'file.key'): {path}")

        # The first element is the TOML file name.
        namespace = keys[0]

        # Lazy Loading: Loads only the necessary file
        if namespace not in self._cache:
            self._load_file(namespace)

        try:
            # Navigate through nested keys using reduce.
            value = reduce(operator.getitem, keys[1:], self._cache[namespace])
        except (KeyError, TypeError) as error:
            logger.error(f'Key not found in prompt: {path}')
            raise PromptNotFoundError(f"Prompt key not found: {path}") from error

        if not isinstance(value, str):
            logger.warning(f'The prompt path "{path}" does not point to a final string.')

            return str(value)

        return value.strip()


@lru_cache(maxsize=1)
def get_prompt_manager(prompts_dir: Path = Cfg.PROMPTS_DIR) -> PromptManagerProtocol:
    """Factory to get the PromptManager instance (Singleton)."""

    return PromptManager(prompts_dir=prompts_dir)
