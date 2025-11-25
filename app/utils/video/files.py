from pathlib import Path
from tempfile import mkdtemp

from app.core.config import settings


def create_temp_dir() -> Path:
    """
    Create temporary directory for processing files.

    Returns:
        Path to created temporary directory
    """
    temp_dir = Path(mkdtemp(dir=settings.TEMP_DIR))
    return temp_dir


def delete_temp_files(
    file_paths: list[str],
) -> None:
    """
    Delete temporary files.

    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists():
            path.unlink()

