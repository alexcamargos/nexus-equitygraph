"""Unit tests for the PromptManager class."""

import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from nexus_equitygraph.core.exceptions import PromptError, PromptNotFoundError
from nexus_equitygraph.core.prompt_manager import PromptManager, get_prompt_manager


class TestPromptManager:
    """Test suite for PromptManager."""

    @pytest.fixture
    def mock_prompts_dir(self, tmp_path):
        """Fixture providing a temporary directory for prompts."""

        return tmp_path / "prompts"

    @pytest.fixture
    def manager(self, mock_prompts_dir):
        """Fixture providing a PromptManager instance."""

        return PromptManager(prompts_dir=mock_prompts_dir)

    def test_initialization(self, manager, mock_prompts_dir):
        """Test proper initialization of PromptManager."""

        # Act: Access attributes to verify state.
        cache_state = manager._cache
        dir_state = manager.prompts_dir

        # Assert: Verify initial empty state and correct directory.
        assert cache_state == {}
        assert dir_state == mock_prompts_dir

    def test_load_file_success(self, manager, mocker):
        """Test successful loading of a TOML file."""

        # Arrange: Mock file existence and content.
        namespace = "agent"
        toml_content = b'["slm"]\nsystem_message = "Hello World"'

        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch("builtins.open", mocker.mock_open(read_data=toml_content))

        # Act: Load the file explicitly.
        manager._load_file(namespace)

        # Assert: Verify cache is populated correctly.
        assert namespace in manager._cache
        assert manager._cache[namespace]["slm"]["system_message"] == "Hello World"

    def test_load_file_not_found(self, manager, mocker):
        """Test handling of missing prompt files."""

        # Arrange: Mock file not found.
        mocker.patch.object(Path, "exists", return_value=False)
        namespace = "missing_file"

        # Act: Attempt to load the file.
        manager._load_file(namespace)

        # Assert: Verify cache contains empty dict for namespace to prevent retries.
        assert manager._cache[namespace] == {}

    def test_load_file_toml_error(self, manager, mocker):
        """Test handling of malformed TOML files."""

        # Arrange: Mock TOML decode error.
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch("builtins.open", mocker.mock_open(read_data=b"invalid"))
        mocker.patch("tomllib.load", side_effect=tomllib.TOMLDecodeError("Invalid TOML"))
        namespace = "broken_file"

        # Act: Attempt to load the file.
        manager._load_file(namespace)

        # Assert: Verify cache handles error gracefully (empty dict).
        assert manager._cache[namespace] == {}

    def test_load_file_validation_error(self, manager, mocker):
        """Test handling of schema validation errors."""

        # Arrange: Mock validation error during schema creation.
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch("builtins.open", mocker.mock_open(read_data=b"key='val'"))
        # Patch PromptSchema to raise ValidationError
        mocker.patch(
            "nexus_equitygraph.core.prompt_manager.PromptSchema",
            side_effect=ValidationError.from_exception_data("msg", []),
        )
        namespace = "invalid_schema"

        # Act: Attempt to load the file.
        manager._load_file(namespace)

        # Assert: Verify cache handles error gracefully.
        assert manager._cache[namespace] == {}

    def test_load_file_os_error(self, manager, mocker):
        """Test handling of OS errors during file reading."""

        # Arrange: Mock OSError on file open.
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch("builtins.open", side_effect=OSError("Disk error"))
        namespace = "os_error"

        # Act: Attempt to load the file.
        manager._load_file(namespace)

        # Assert: Verify cache handles error gracefully.
        assert manager._cache[namespace] == {}

    def test_get_success(self, manager):
        """Test retrieving a valid prompt string."""

        # Arrange: Pre-populate cache.
        manager._cache = {"agent": {"slm": {"system_message": "  You are helpful.  "}}}
        path = "agent.slm.system_message"

        # Act: Retrieve the prompt.
        result = manager.get(path)

        # Assert: Verify the string is returned and stripped.
        assert result == "You are helpful."

    def test_get_lazy_loading(self, manager, mocker):
        """Test that get() triggers file loading if namespace is missing."""

        # Arrange: Mock _load_file to verify interaction and simulate cache population.
        def side_effect_load(namespace):
            manager._cache[namespace] = {"key": "loaded_value"}

        mock_load = mocker.patch.object(manager, "_load_file", side_effect=side_effect_load)
        path = "dynamic.key"

        # Act: Request a path not currently in cache.
        result = manager.get(path)

        # Assert: Verify load was triggered and value returned.
        mock_load.assert_called_once_with("dynamic")
        assert result == "loaded_value"

    def test_get_invalid_path_format(self, manager):
        """Test error when path format is incorrect."""

        # Arrange: Path without dot separator.
        path = "invalid_path"

        # Act & Assert: Expect PromptError.
        with pytest.raises(PromptError, match="Invalid prompt path"):
            manager.get(path)

    def test_get_key_not_found(self, manager):
        """Test error when key does not exist in loaded structure."""

        # Arrange: Cache exists.
        manager._cache = {"agent": {"existing": "val"}}
        path = "agent.missing"

        # Act & Assert: Expect PromptNotFoundError.
        with pytest.raises(PromptNotFoundError, match="Prompt key not found"):
            manager.get(path)

    def test_get_non_string_value(self, manager):
        """Test retrieving a non-string value (should be cast to string)."""

        # Arrange: Cache contains an integer.
        manager._cache = {"config": {"retries": 5}}
        path = "config.retries"

        # Act: Retrieve the value.
        result = manager.get(path)

        # Assert: Verify it is converted to string.
        assert result == "5"

    def test_clear_cache(self, manager):
        """Test clearing the cache."""

        # Arrange: Populate cache.
        manager._cache = {"data": "cached"}

        # Act: Clear the cache.
        manager.clear_cache()

        # Assert: Verify cache is empty.
        assert manager._cache == {}


def test_get_prompt_manager_singleton():
    """Test that get_prompt_manager returns a singleton instance."""

    # Act: Call the factory twice.
    instance1 = get_prompt_manager()
    instance2 = get_prompt_manager()

    # Assert: Verify both references point to the same object.
    assert instance1 is instance2
