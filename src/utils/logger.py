"""Structured logging configuration for the trading system."""

import logging
import sys
from pathlib import Path

from .config import config


def setup_logger(
    name: str = "tradeagent",
    log_file: str | None = "logs/trading.log",
    level: str | None = None,
) -> logging.Logger:
    """Set up and configure a logger with console and file handlers.

    Args:
        name: Logger name
        log_file: Path to log file (creates directory if needed)
        level: Log level (uses config.LOG_LEVEL if not provided)

    Returns:
        Configured logger instance
    """
    # Use config log level if not explicitly provided
    if level is None:
        level = config.LOG_LEVEL

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()
