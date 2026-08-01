"""Logging configuration and the shared application logger.

The application uses a single named logger (see APP_LOGGER_NAME) obtained
through get_logger(). Console output is colored when Rich is installed, and
all records are mirrored to a rotating file in the configured log directory.

Configuration is idempotent: calling configure_logging repeatedly never
duplicates handlers.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config.constants import (
    APP_LOGGER_NAME,
    CONSOLE_HANDLER_NAME,
    FILE_HANDLER_NAME,
    LOG_DATE_FORMAT,
    LOG_FILE_BACKUP_COUNT,
    LOG_FILE_MAX_BYTES,
    LOG_FILE_NAME,
    LOG_FORMAT,
)
from app.config.settings import Settings
from app.utils.helpers import ensure_directory

try:
    from rich.logging import RichHandler
except ImportError:
    RichHandler = None


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the shared application logger.

    Without a name the single application logger is returned. Providing a
    name yields a child logger (e.g. ``lead_generation_agent.agent``) that
    shares the application's handlers.
    """
    logger_name = APP_LOGGER_NAME if name is None else f"{APP_LOGGER_NAME}.{name}"
    return logging.getLogger(logger_name)


def configure_logging(settings: Settings) -> None:
    """Configure console and file logging for the whole application."""
    ensure_directory(settings.log_dir)
    level = settings.log_level.upper()
    root = logging.getLogger()
    root.setLevel(level)

    if not _has_handler(CONSOLE_HANDLER_NAME):
        console_handler = _build_console_handler(level)
        console_handler.set_name(CONSOLE_HANDLER_NAME)
        root.addHandler(console_handler)

    if not _has_handler(FILE_HANDLER_NAME):
        file_handler = _build_file_handler(settings.log_dir, level)
        file_handler.set_name(FILE_HANDLER_NAME)
        root.addHandler(file_handler)


def _build_console_handler(level: str) -> logging.Handler:
    """Return a colored console handler, falling back to plain output."""
    if RichHandler is not None:
        return RichHandler(level=level, show_time=False, show_path=False, markup=False)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    return handler


def _build_file_handler(log_dir: Path, level: str) -> logging.Handler:
    """Return a rotating file handler for the application log file."""
    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    return handler


def _has_handler(name: str) -> bool:
    """Return True if the root logger already has a handler with the name."""
    return any(getattr(handler, "name", None) == name for handler in logging.getLogger().handlers)
