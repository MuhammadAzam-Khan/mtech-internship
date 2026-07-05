"""
logger.py
----------
Centralized logging configuration for the Customer Sentiment Analyzer.

All application events (errors, imports, predictions, exports, and general
system events) are written to a rotating log file inside the `logs/`
directory, and also echoed to the console during development.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

_LOGGER_NAME = "SentimentAnalyzer"


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """
    Create (or retrieve) a configured logger instance.

    Args:
        name: Name of the logger, useful for identifying the module
              that produced a given log entry.

    Returns:
        A configured `logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Logger already configured, avoid duplicate handlers.
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Convenience module-level logger used across the application.
app_logger = get_logger()


def log_event(category: str, message: str, level: str = "info") -> None:
    """
    Log a categorized application event.

    Args:
        category: One of "IMPORT", "PREDICTION", "EXPORT", "SYSTEM", "ERROR".
        message: Human readable description of the event.
        level: Logging level ("debug", "info", "warning", "error", "critical").
    """
    formatted = f"[{category.upper()}] {message}"
    log_fn = getattr(app_logger, level.lower(), app_logger.info)
    log_fn(formatted)
