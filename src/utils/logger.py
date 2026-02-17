"""Centralized logging configuration."""
from __future__ import annotations

import logging
import sys
import asyncio
from pathlib import Path
from typing import Any

from .config import config

class PostgresLogHandler(logging.Handler):
    """Logging handler that writes to PostgreSQL asynchronously."""
    
    def emit(self, record: logging.LogRecord):
        """Queue log record for writing."""
        if record.levelno < logging.WARNING:
            return
            
        try:
            msg = self.format(record)
            log_data = {
                "level": record.levelname,
                "module": record.name,
                "message": msg,
                "trace": None
            }
            
            if record.exc_info:
                from logging import Formatter
                log_data["trace"] = Formatter().formatException(record.exc_info)
                
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._flush_to_db(log_data))
            except RuntimeError:
                pass
        except Exception:
            self.handleError(record)

    async def _flush_to_db(self, data: dict[str, Any]):
        """Write to Database via lazy import."""
        try:
            # Absolute import to be safe and avoid circular imports
            from src.database.postgres_client import PostgresClient
            await PostgresClient.log_system_event(
                level=data["level"],
                module=data["module"],
                message=data["message"],
                trace=data["trace"]
            )
        except Exception as e:
            # Critical: Use print to stderr to avoid infinite recursion
            print(f"PostgresLogHandler critical failure: {e}", file=sys.stderr)

def setup_logger(
    name: str = "tradeagent",
    log_file: str | None = "logs/trading.log",
    level: str | None = None,
) -> logging.Logger:
    """Set up and configure a logger with console, file, and DB handlers."""
    if level is None:
        level = config.LOG_LEVEL

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if logger.handlers:
        return logger

    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"))
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    if hasattr(config, "POSTGRES_URL") and config.POSTGRES_URL:
        db_handler = PostgresLogHandler()
        db_handler.setLevel(logging.WARNING)
        db_handler.setFormatter(detailed_formatter)
        logger.addHandler(db_handler)

    return logger

logger = setup_logger()
