"""Tests for the directory creation utility in nexus_equitygraph.core.tools module."""

from pathlib import Path

import pytest

from nexus_equitygraph.core.tools import ensure_directory_exists


class TestEnsureDirectoryExists:
    """Test suite for directory creation utility."""

    def test_creates_directory(self, tmp_path):
        """Tests if the directory is created correctly."""

        # Setup: Define target directory path.
        target_dir = tmp_path / "new_dir"

        # Action: Call the function to create the directory.
        ensure_directory_exists(target_dir)

        # Assert: Verify the directory was created.
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_creates_nested_directories(self, tmp_path):
        """Tests if nested directories (parents) are created."""

        # Setup: Define target directory path.
        target_dir = tmp_path / "level1" / "level2"

        # Action: Call the function to create nested directories.
        ensure_directory_exists(target_dir)

        # Assert: Verify the nested directories were created.
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_idempotent(self, tmp_path):
        """Tests if calling on an existing directory does not raise error."""

        # Setup: Create the directory beforehand.
        target_dir = tmp_path / "existing_dir"
        target_dir.mkdir()

        # Action: Call ensure_directory_exists on the existing directory.
        ensure_directory_exists(target_dir)

        # Assert: Verify the directory still exists.
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_raises_if_file_exists(self, tmp_path):
        """Tests if NotADirectoryError is raised when path is a file."""

        # Setup: Create a file at the target path.
        file_path = tmp_path / "file.txt"
        file_path.touch()

        # Action & Assert: Verify NotADirectoryError is raised.
        with pytest.raises(NotADirectoryError, match="exists and is not a directory"):
            ensure_directory_exists(file_path)

    def test_raises_os_error(self, mocker):
        """Tests if generic OSError is re-raised correctly."""

        # Setup: Mock Path.mkdir to raise OSError.
        mock_path = mocker.MagicMock(spec=Path)
        
        # Simulate a permission error or other OS level failure
        mock_path.mkdir.side_effect = OSError("Disk full")

        # Action & Assert: Verify OSError is raised.
        with pytest.raises(OSError, match="Failed to create directory"):
            ensure_directory_exists(mock_path)
