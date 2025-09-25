"""Logger configuration bootstrap.

Where: platform/logging/config.py
What: Configure global logging defaults and expose the shared application logger.
Why: Separate handler formatting from setup so configuration stays concise.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Final

from rich.console import Console

from omym.config.paths import default_log_file

from .handlers import WhitePathRichHandler


DEFAULT_LOG_FILE: Final[Path] = default_log_file()


def setup_logger(
    log_file: Path | None = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> logging.Logger:
    """Set up and configure the application logger."""

    logger = logging.getLogger("omym")
    logger.setLevel(logging.DEBUG)

    for handler in list(logger.handlers):
        handler.close()
    logger.handlers.clear()

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console = Console(force_terminal=True, soft_wrap=True)
    console_handler = WhitePathRichHandler(console=console)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)

    if log_file is not None:
        resolved_log_file = Path(log_file).expanduser().resolve()
        os.makedirs(resolved_log_file.parent, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            resolved_log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


logger: Final[logging.Logger] = setup_logger(log_file=DEFAULT_LOG_FILE)


__all__ = ["DEFAULT_LOG_FILE", "setup_logger", "logger"]
