"""Utility tools for core functionality of the Nexus Equity Graph application."""

from pathlib import Path


def ensure_directory_exists(directory_path: Path) -> None:
    """Ensure that a directory exists; create it if it does not.
    
    The directory is created in an easier manner, including any necessary parent directories.

    Args:
        directory_path (Path): The path to the directory to ensure.

    Raises:
        NotADirectoryError: If the path exists but is not a directory.
    """

    try:
        # Create the directory and any necessary parent directories.
        directory_path.mkdir(parents=True, exist_ok=True)
    except FileExistsError as error:
        raise NotADirectoryError(f"The path {directory_path} exists and is not a directory.") from error
    except OSError as error:
        raise OSError(f"Failed to create directory {directory_path}: {error}") from error
