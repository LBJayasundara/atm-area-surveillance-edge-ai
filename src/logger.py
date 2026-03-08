"""
Logging configuration module for ATM Surveillance system.

Provides a rotating file logger with console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name: str, log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """
    Create and configure a logger with rotating file handler and console output.

    Args:
        name: Logger name, typically the module name.
        log_dir: Directory where log files will be stored.
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured Logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers when module is re-imported
    if logger.handlers:
        return logger

    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler — 5 MB per file, keep 5 backups
    log_file = os.path.join(log_dir, "surveillance.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(log_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
