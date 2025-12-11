import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkdtemp
from typing import Generator

from app.core.config import settings


def create_temp_dir() -> Path:
    """
    Create temporary directory for processing files.

    Returns:
        Path to created temporary directory
    """
    temp_dir = Path(mkdtemp(dir=settings.TEMP_DIR))
    return temp_dir


def create_temp_file(
    suffix: str = "",
    prefix: str = "tmp",
) -> str:
    """
    Create temporary file with proper cleanup handling.

    Args:
        suffix: File suffix (extension)
        prefix: File prefix

    Returns:
        Path to created temporary file
    """
    temp_fd, temp_path = tempfile.mkstemp(
        suffix=suffix,
        prefix=prefix,
        dir=settings.TEMP_DIR,
    )
    os.close(temp_fd)
    return temp_path


@contextmanager
def temp_file_context(
    suffix: str = "",
    prefix: str = "tmp",
) -> Generator[str, None, None]:
    """
    Context manager for temporary file with automatic cleanup.

    Args:
        suffix: File suffix (extension)
        prefix: File prefix

    Yields:
        Path to temporary file
    """
    temp_path = create_temp_file(
        suffix=suffix,
        prefix=prefix,
    )
    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def delete_temp_files(
    file_paths: list[str],
) -> None:
    """
    Delete temporary files safely.

    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        if not file_path:
            continue
        
        path = Path(file_path)
        if path.exists():
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
            except Exception:
                pass

