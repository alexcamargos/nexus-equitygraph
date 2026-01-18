"""Unit tests for configs module."""

from pathlib import Path

import pytest

from nexus_equitygraph.core.configs import DirectoryConfigs


class TestDirectoryConfigs:
    """Tests for DirectoryConfigs dataclass."""

    @pytest.fixture
    def config(self):
        """Create a DirectoryConfigs instance for testing."""

        return DirectoryConfigs()

    def test_base_directory_is_path(self, config: DirectoryConfigs):
        """Verify BASE_DIRECTORY is a Path object."""

        # Act: Retrieve the BASE_DIRECTORY attribute.
        result = config.BASE_DIRECTORY

        # Assert: The result should be an instance of Path.
        assert isinstance(result, Path)

    def test_data_directory_is_path(self, config: DirectoryConfigs):
        """Verify DATA_DIRECTORY is a Path object."""

        # Act: Retrieve the DATA_DIRECTORY attribute.
        result = config.DATA_DIRECTORY

        # Assert: The result should be an instance of Path.
        assert isinstance(result, Path)

    def test_data_directory_is_under_base(self, config: DirectoryConfigs):
        """Verify DATA_DIRECTORY is a child of BASE_DIRECTORY."""

        # Act: Get the parent of DATA_DIRECTORY.
        parent = config.DATA_DIRECTORY.parent

        # Assert: The parent should be the BASE_DIRECTORY.
        assert parent == config.BASE_DIRECTORY

    def test_cvm_subdirectory_is_under_data(self, config: DirectoryConfigs):
        """Verify CVM_SUB_DIRECTORY is a child of DATA_DIRECTORY."""

        # Act: Get the parent of CVM_SUB_DIRECTORY.
        parent = config.CVM_SUB_DIRECTORY.parent

        # Assert: The parent should be the DATA_DIRECTORY.
        assert parent == config.DATA_DIRECTORY

    def test_log_directory_is_under_data(self, config: DirectoryConfigs):
        """Verify LOG_DIRECTORY is a child of DATA_DIRECTORY."""

        # Act: Get the parent of LOG_DIRECTORY.
        parent = config.LOG_DIRECTORY.parent

        # Assert: The parent should be the DATA_DIRECTORY.
        assert parent == config.DATA_DIRECTORY

    def test_news_subdirectory_is_under_data(self, config: DirectoryConfigs):
        """Verify NEWS_SUB_DIRECTORY is a child of DATA_DIRECTORY."""

        # Act: Get the parent of NEWS_SUB_DIRECTORY.
        parent = config.NEWS_SUB_DIRECTORY.parent

        # Assert: The parent should be the DATA_DIRECTORY.
        assert parent == config.DATA_DIRECTORY

    def test_dataclass_is_frozen(self, config: DirectoryConfigs):
        """Verify DirectoryConfigs is immutable (frozen)."""

        # Act & Assert: Attempting to modify an attribute should raise AttributeError.
        with pytest.raises(AttributeError):
            config.BASE_DIRECTORY = Path("/tmp")  # type: ignore

    def test_data_directory_name(self, config: DirectoryConfigs):
        """Verify DATA_DIRECTORY has correct name."""

        # Act: Get the name of DATA_DIRECTORY.
        name = config.DATA_DIRECTORY.name

        # Assert: The directory name should be 'data'.
        assert name == "data"

    def test_cvm_subdirectory_name(self, config: DirectoryConfigs):
        """Verify CVM_SUB_DIRECTORY has correct name."""

        # Act: Get the name of CVM_SUB_DIRECTORY.
        name = config.CVM_SUB_DIRECTORY.name

        # Assert: The directory name should be 'cvm'.
        assert name == "cvm"

    def test_log_directory_name(self, config: DirectoryConfigs):
        """Verify LOG_DIRECTORY has correct name."""

        # Act: Get the name of LOG_DIRECTORY.
        name = config.LOG_DIRECTORY.name

        # Assert: The directory name should be 'logs'.
        assert name == "logs"

    def test_news_subdirectory_name(self, config: DirectoryConfigs):
        """Verify NEWS_SUB_DIRECTORY has correct name."""

        # Act: Get the name of NEWS_SUB_DIRECTORY.
        name = config.NEWS_SUB_DIRECTORY.name

        # Assert: The directory name should be 'news'.
        assert name == "news"

    def test_all_paths_are_absolute(self, config: DirectoryConfigs):
        """Verify all directory paths are absolute."""

        # Act: Check if each path is absolute.
        base_is_absolute = config.BASE_DIRECTORY.is_absolute()
        data_is_absolute = config.DATA_DIRECTORY.is_absolute()
        cvm_is_absolute = config.CVM_SUB_DIRECTORY.is_absolute()
        log_is_absolute = config.LOG_DIRECTORY.is_absolute()
        news_is_absolute = config.NEWS_SUB_DIRECTORY.is_absolute()

        # Assert: All paths should be absolute.
        assert base_is_absolute
        assert data_is_absolute
        assert cvm_is_absolute
        assert log_is_absolute
        assert news_is_absolute
