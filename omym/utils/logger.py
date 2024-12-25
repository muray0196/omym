"""Centralized logging configuration for OMYM."""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


def setup_logger(
    log_file: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> logging.Logger:
    """Set up and configure the application logger.

    Args:
        log_file: Path to the log file. If None, only console logging is enabled.
        console_level: Logging level for console output. Defaults to INFO.
        file_level: Logging level for file output. Defaults to DEBUG.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger("omym")
    logger.setLevel(logging.DEBUG)

    # Create formatters
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file is not None:
        # Ensure the log directory exists
        os.makedirs(log_file.parent, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()
