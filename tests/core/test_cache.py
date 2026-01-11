"""Tests for the caching mechanism in nexus_equitygraph.core.cache module."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nexus_equitygraph.core.cache import CacheManager, JSONCacheManager, get_json_cache_manager


class TestCacheManager:
    """Test suite for the base CacheManager class."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Fixture providing a CacheManager instance rooted in tmp_path."""

        return CacheManager(base_directory=tmp_path)

    def test_init_ensures_directory_exists(self, tmp_path):
        """Tests if initialization creates the base directory if it doesn't exist."""

        # Setup: Define a path that does not exist yet.
        cache_dir = tmp_path / "cache_data"

        # Action: Initialize CacheManager.
        CacheManager(base_directory=cache_dir)

        # Assert: Verify the directory was created.
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_get_cache_file_path(self, manager, tmp_path):
        """Tests path construction logic."""

        # Action: Get cache file path.
        path = manager._get_cache_file_path("subdir", "file.json")

        # Assert: Verify the constructed path is correct.
        assert path == tmp_path / "subdir" / "file.json"

    def test_is_cache_valid_file_not_exists(self, manager, tmp_path):
        """Tests validation returns False if file does not exist."""

        # Action: Define a non-existent file path.
        file_path = tmp_path / "non_existent.json"

        # Assert: Validation should return False.
        assert manager.is_cache_valid(file_path) is False

    def test_is_cache_valid_fresh_file(self, manager, tmp_path):
        """Tests validation returns True for a fresh file."""

        # Action: Create a fresh file.
        file_path = tmp_path / "fresh.json"
        file_path.touch()  # Creates file with current timestamp

        # Assert: Validation should return True.
        assert manager.is_cache_valid(file_path) is True

    def test_is_cache_valid_expired_file(self, manager, tmp_path):
        """Tests validation returns False for an expired file."""

        # Action: Create a file and modify its mtime to be old.
        file_path = tmp_path / "expired.json"
        file_path.touch()

        # Setup: Modify mtime to be 2 days ago
        two_days_ago = (datetime.now() - timedelta(days=2)).timestamp()
        os.utime(file_path, (two_days_ago, two_days_ago))

        # Assert: Default expiry is 1 day, so it should be invalid
        assert manager.is_cache_valid(file_path) is False

    def test_is_cache_valid_os_error(self, manager, mocker):
        """Tests validation handles OSError gracefully (e.g., permission issues)."""

        # Mock a Path object to simulate OSError on stat()
        mock_path = mocker.MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.side_effect = OSError("Mock permission error")
        mock_logger = mocker.patch("nexus_equitygraph.core.cache.logger.error")

        # Action & Assert: Validation should return False and log an error.
        assert manager.is_cache_valid(mock_path) is False
        mock_logger.assert_called_once()


class TestJSONCacheManager:
    """Test suite for JSONCacheManager specific logic."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Fixture providing a JSONCacheManager instance rooted in tmp_path."""

        return JSONCacheManager(base_directory=tmp_path)

    def test_save_cache_success(self, manager, tmp_path):
        """Tests saving valid JSON data."""

        # Action: Save some data.
        data = {"key": "value", "number": 123}
        manager.save_cache("subdir", "data.json", data)

        # Assert: Verify file was created with correct content.
        file_path = tmp_path / "subdir" / "data.json"
        assert file_path.exists()

        with open(file_path, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        assert loaded == data

    def test_save_cache_serialization_error(self, manager, mocker):
        """Tests handling of non-serializable data (TypeError)."""

        # Mock logger to verify error logging.
        mock_logger = mocker.patch("nexus_equitygraph.core.cache.logger.error")

        # Sets are not JSON serializable by default.
        data = {"key": {1, 2, 3}}
        manager.save_cache("subdir", "bad_data.json", data)

        # Assert: Verify error was logged.
        mock_logger.assert_called_once()
        assert "JSON encoding error" in mock_logger.call_args[0][0]

    def test_load_cache_success(self, manager, tmp_path):
        """Tests loading valid cached data."""

        # Setup: Pre-create the file manually
        data = {"key": "value"}
        subdir = "subdir"
        filename = "data.json"

        file_path = tmp_path / subdir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file)

        # Action: Load the data using the manager.
        loaded_data = manager.load_cache(subdir, filename)

        # Assert: Verify loaded data matches the original.
        assert loaded_data == data

    def test_load_cache_expired(self, manager, tmp_path):
        """Tests loading returns None if cache is expired."""

        # Setup: Pre-create an expired file.
        file_path = tmp_path / "subdir" / "expired.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        # Setup: Set mtime to past.
        past = (datetime.now() - timedelta(days=2)).timestamp()
        os.utime(file_path, (past, past))

        # Action: Attempt to load expired cache.
        result = manager.load_cache("subdir", "expired.json")

        # Assert: Should return None due to expiry.
        assert result is None

    def test_load_cache_json_error(self, manager, tmp_path, mocker):
        """Tests handling of corrupted JSON files."""

        # Mock logger to verify error logging.
        mock_logger = mocker.patch("nexus_equitygraph.core.cache.logger.error")

        # Setup: Create a file with invalid JSON.
        file_path = tmp_path / "subdir" / "corrupt.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup: Write invalid JSON
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("{invalid-json-content")

        # Action: Attempt to load corrupted cache.
        result = manager.load_cache("subdir", "corrupt.json")

        # Assert: Should return None and log an error.
        assert result is None
        mock_logger.assert_called_once()
        assert "JSON decoding error" in mock_logger.call_args[0][0]

    def test_load_cache_os_error(self, manager, tmp_path, mocker):
        """Tests handling of OSError during file reading (e.g. permission denied)."""
        mock_logger = mocker.patch("nexus_equitygraph.core.cache.logger.error")

        # Setup: Create a valid file so is_cache_valid passes
        file_path = tmp_path / "subdir" / "valid.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        # Mock open to raise OSError.
        mocker.patch("builtins.open", side_effect=OSError("Read error"))

        # Action: Attempt to load cache which triggers OSError.
        result = manager.load_cache("subdir", "valid.json")

        # Assert: Should return None and log an error.
        assert result is None
        mock_logger.assert_called_once()
        assert "Error loading cache" in mock_logger.call_args[0][0]

    def test_save_cache_os_error(self, manager, mocker):
        """Tests handling of OSError during file writing (e.g. disk full)."""
        mock_logger = mocker.patch("nexus_equitygraph.core.cache.logger.error")

        # Mock open to raise OSError.
        mocker.patch("builtins.open", side_effect=OSError("Write error"))

        # Mock ensure_directory_exists to avoid filesystem ops during this specific test.
        mocker.patch("nexus_equitygraph.core.cache.ensure_directory_exists")

        # Action: Attempt to save cache which triggers OSError.
        manager.save_cache("subdir", "file.json", {"key": "value"})

        # Assert: Should log an error due to OSError.
        mock_logger.assert_called_once()
        assert "Error saving cache" in mock_logger.call_args[0][0]

    def test_factory_singleton(self, tmp_path):
        """Tests if get_json_cache_manager returns singleton instances."""

        # Clear cache first to ensure isolation from other tests
        get_json_cache_manager.cache_clear()

        # Action: Get two instances.
        instance1 = get_json_cache_manager(tmp_path)
        instance2 = get_json_cache_manager(tmp_path)

        # Assert: Both instances should be the same.
        assert instance1 is instance2
        assert isinstance(instance1, JSONCacheManager)
