import logging
import sys
from typing import Any


def setup_logging(
    level: str = "INFO",
) -> None:
    """
    Setup structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(
    name: str,
) -> logging.Logger:
    """
    Get logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_error(
    logger: logging.Logger,
    message: str,
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log error with context.

    Args:
        logger: Logger instance
        message: Error message
        error: Exception object
        context: Additional context dictionary
    """
    context_str = ""
    if context:
        context_items = [f"{k}={v}" for k, v in context.items()]
        context_str = f" | Context: {', '.join(context_items)}"

    logger.error(
        f"{message} | Error: {type(error).__name__}: {str(error)}{context_str}",
        exc_info=True,
    )

