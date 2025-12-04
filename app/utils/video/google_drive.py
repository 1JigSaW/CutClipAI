import re
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def extract_file_id_from_url(
    url: str,
) -> str | None:
    """
    Extract Google Drive file ID from URL.

    Args:
        url: Google Drive sharing URL

    Returns:
        File ID or None if not found
    """
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/open\?id=([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            logger.debug(f"Extracted file ID from URL | file_id={file_id}")
            return file_id

    logger.warning(f"Failed to extract file ID from URL | url={url[:50]}...")
    return None


def get_download_url_via_api(
    file_id: str,
) -> str | None:
    """
    Get Google Drive file download URL using API.

    Args:
        file_id: Google Drive file ID

    Returns:
        Direct download URL via API or None if API key is not set
    """
    api_key = settings.GOOGLE_DRIVE_API_KEY

    if not api_key:
        logger.error("GOOGLE_DRIVE_API_KEY is not set in configuration")
        return None

    download_url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}?"
        f"alt=media&key={api_key}"
    )

    logger.debug(f"Generated Google Drive API download URL | file_id={file_id}")
    return download_url


def is_google_drive_url(
    url: str,
) -> bool:
    """
    Check if URL is a Google Drive URL.

    Args:
        url: URL to check

    Returns:
        True if URL is Google Drive, False otherwise
    """
    parsed = urlparse(url)
    return "drive.google.com" in parsed.netloc.lower()

