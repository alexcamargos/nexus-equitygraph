"""Cache management module for Nexus EquityGraph."""

import json
import pickle
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .configs import DirectoryConfigs as Cfg
from .tools import ensure_directory_exists


# pylint: disable=too-few-public-methods
class CacheManager:
    """Base class for cache managers.

    Args:
        base_directory (Path): The base directory for cache storage.

    Methods:
        _get_cache_file_path(sub_directory: Path | str, file_name: str)
            Get the full path for a cache file.
        is_cache_valid(file_path: Path, expiry_duration: timedelta)
            Check if the cache file is still valid based on the expiry duration.
    """

    def __init__(self, base_directory: Path = Cfg.DATA_DIRECTORY) -> None:
        """Initialize the CacheManager with a base directory.

        Args:
            base_directory (Path): The base directory for cache storage.
                                   Defaults to the DATA_DIRECTORY from DirectoryConfigs.
        """

        self.base_directory = base_directory

        # Ensure the base directory exists.
        ensure_directory_exists(self.base_directory)

    def _get_cache_file_path(self, sub_directory: Path | str, file_name: str) -> Path:
        """Get the full path for a cache file.

        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.

        Returns:
            Path: The full path for the cache file.
        """

        return self.base_directory / sub_directory / file_name

    def get_file_path(self, sub_directory: Path | str, file_name: str) -> Path:
        """Public method to get the full path for a cache file.

        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
        """

        return self._get_cache_file_path(sub_directory, file_name)

    def is_cache_valid(
        self, file_path: Path, expiry_duration: timedelta = timedelta(days=1)
    ) -> bool:
        """Check if the cache file is still valid based on the expiry duration.

        Args:
            file_path (Path): The path to the cache file.
            expiry_duration (timedelta): The duration after which the cache is considered expired.
                                         Defaults to 1 day.

        Returns:
            bool: True if the cache is valid, False otherwise.
        """

        if not file_path.exists():
            return False

        try:
            file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if datetime.now() - file_mod_time > expiry_duration:
                return False
        except OSError as error:
            logger.error(f"Error checking cache validity for {file_path}: {error}")
            return False

        return True


class JSONCacheManager(CacheManager):
    """Cache manager for JSON files

    Methods:
        load_cache(sub_directory: Path | str, file_name: str, expiry_duration: timedelta)
            Load cached data from a JSON file if valid.
        save_cache(sub_directory: Path | str, file_name: str, data: Dict[str, Any])
            Save data to a JSON cache file.
    """

    def load_cache(
        self,
        sub_directory: Path | str,
        file_name: str,
        expiry_duration: timedelta = timedelta(days=1),
    ) -> Optional[Dict[str, Any]]:
        """Load cached data from a JSON file if valid.

        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
            expiry_duration (timedelta): The duration after which the cache is considered expired.
                                         Defaults to 1 day.

        Returns:
            Optional[Dict[str, Any]]: The cached data if valid, None otherwise.

        Raises:
            json.JSONDecodeError: If there is an error decoding the JSON data.
            OSError: If there is an error loading the cache file.
        """

        file_path = self._get_cache_file_path(sub_directory, file_name)

        if not self.is_cache_valid(file_path, expiry_duration):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data
        except json.JSONDecodeError as json_error:
            logger.error(
                f"JSON decoding error when loading cache from {file_path}: {json_error}"
            )
        except OSError as os_error:
            logger.error(f"Error loading cache from {file_path}: {os_error}")

        return None

    def save_cache(
        self, sub_directory: Path | str, file_name: str, data: Dict[str, Any]
    ) -> None:
        """Save data to a JSON cache file.

        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
            data (Dict[str, Any]): The data to be cached.

        Raises:
            TypeError: If the data cannot be serialized to JSON.
            OSError: If there is an error saving the cache file.
        """

        file_path = self._get_cache_file_path(sub_directory, file_name)

        # Ensure the subdirectory exists.
        ensure_directory_exists(file_path.parent)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except TypeError as type_error:
            logger.error(
                f"JSON encoding error (serialization) when saving cache to {file_path}: {type_error}"
            )
        except OSError as os_error:
            logger.error(f"Error saving cache to {file_path}: {os_error}")


class PickleCacheManager(CacheManager):
    """Cache manager for Pickle files (Python Objects).
    
    Methods:
        load_cache(sub_directory: Path | str, file_name: str, expiry_duration: timedelta)
            Load cached data from a Pickle file if valid.
        save_cache(sub_directory: Path | str, file_name: str, data: Any)
            Save data to a Pickle cache file.
    """

    def load_cache(
        self,
        sub_directory: Path | str,
        file_name: str,
        expiry_duration: timedelta = timedelta(days=7),
    ) -> Optional[Any]:
        """Load cached data from a Pickle file if valid.
        
        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
            expiry_duration (timedelta): The duration after which the cache is considered expired.
                                         Defaults to 7 days.

        Returns:
            Optional[Any]: The cached data if valid, None otherwise.

        Raises:
            pickle.UnpicklingError: If there is an error unpickling the data.
            OSError: If there is an error loading the cache file.
        """

        file_path = self._get_cache_file_path(sub_directory, file_name)

        if not self.is_cache_valid(file_path, expiry_duration):
            return None

        try:
            with open(file_path, "rb") as file:
                return pickle.load(file)
        except (pickle.UnpicklingError, EOFError) as pkl_error:
            logger.error(
                f"Pickle error when loading cache from {file_path}: {pkl_error}"
            )
        except OSError as os_error:
            logger.error(f"Error loading cache from {file_path}: {os_error}")

        return None

    def save_cache(self, sub_directory: Path | str, file_name: str, data: Any) -> None:
        """Save data to a Pickle cache file.
        
        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
            data (Any): The data to be cached.

        Raises:
            pickle.PicklingError: If there is an error pickling the data.
            OSError: If there is an error saving the cache file.
        """

        file_path = self._get_cache_file_path(sub_directory, file_name)
        ensure_directory_exists(file_path.parent)

        try:
            with open(file_path, "wb") as file:
                pickle.dump(data, file)
        except (pickle.PicklingError, TypeError) as pkl_error:
            logger.error(f"Pickle error when saving cache to {file_path}: {pkl_error}")
        except OSError as os_error:
            logger.error(f"Error saving cache to {file_path}: {os_error}")


class FileCacheManager(CacheManager):
    """Cache manager for generic binary files (ZIPs, CSVs, PDFs).
    
    Methods:
        load_cache(sub_directory: Path | str, file_name: str, expiry_duration: timedelta)
            Load raw bytes from a file if valid.
        save_cache(sub_directory: Path | str, file_name: str, data: bytes)
            Save raw bytes to a file.
    """

    def load_cache(
        self,
        sub_directory: Path | str,
        file_name: str,
        expiry_duration: timedelta = timedelta(days=30),
    ) -> Optional[bytes]:
        """Load raw bytes from a file if valid.
        
        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
            expiry_duration (timedelta): The duration after which the cache is considered expired.
                                         Defaults to 30 days.

        Returns:
            Optional[bytes]: The cached data if valid, None otherwise.
            
        Raises:
            OSError: If there is an error loading the cache file.    
        """

        file_path = self._get_cache_file_path(sub_directory, file_name)

        if not self.is_cache_valid(file_path, expiry_duration):
            return None

        try:
            with open(file_path, "rb") as file:
                return file.read()
        except OSError as os_error:
            logger.error(f"Error loading file cache from {file_path}: {os_error}")

        return None

    def save_cache(
        self, sub_directory: Path | str, file_name: str, data: bytes
    ) -> None:
        """Save raw bytes to a file.
        
        Args:
            sub_directory (Path | str): The subdirectory within the base directory.
            file_name (str): The name of the cache file.
            data (bytes): The raw bytes to be cached.

        Raises:
            OSError: If there is an error saving the cache file.
        """

        file_path = self._get_cache_file_path(sub_directory, file_name)
        ensure_directory_exists(file_path.parent)

        try:
            with open(file_path, "wb") as file:
                file.write(data)
        except OSError as os_error:
            logger.error(f"Error saving file cache to {file_path}: {os_error}")


@lru_cache(maxsize=1)
def get_json_cache_manager(
    base_directory: Path = Cfg.DATA_DIRECTORY,
) -> JSONCacheManager:
    """Factory to get the JSON cache manager instance (Singleton).

    Args:
        base_directory (Path): The base directory for cache storage.
                               Defaults to the DATA_DIRECTORY from DirectoryConfigs.

    Returns:
        JSONCacheManager: The configured JSON cache manager instance.
    """

    return JSONCacheManager(base_directory)


@lru_cache(maxsize=1)
def get_pickle_cache_manager(
    base_directory: Path = Cfg.DATA_DIRECTORY,
) -> PickleCacheManager:
    """Factory to get the Pickle cache manager instance (Singleton).
    
    Args:
        base_directory (Path): The base directory for cache storage.
                               Defaults to the DATA_DIRECTORY from DirectoryConfigs.

    Returns:
        PickleCacheManager: The configured Pickle cache manager instance.
    """

    return PickleCacheManager(base_directory)


@lru_cache(maxsize=1)
def get_file_cache_manager(
    base_directory: Path = Cfg.DATA_DIRECTORY,
) -> FileCacheManager:
    """Factory to get the File cache manager instance (Singleton).
    
    Args:
        base_directory (Path): The base directory for cache storage.
                               Defaults to the DATA_DIRECTORY from DirectoryConfigs.

    Returns:
        FileCacheManager: The configured File cache manager instance.
    """

    return FileCacheManager(base_directory)


__all__ = [
    "get_json_cache_manager",
    "get_pickle_cache_manager",
    "get_file_cache_manager",
]
