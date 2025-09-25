"""Logging facade exports.

Where: platform/logging/__init__.py
What: Re-export configured logger, setup helpers, and custom Rich handlers.
Why: Provide a single canonical import path without legacy modules.
"""

from __future__ import annotations

from .config import DEFAULT_LOG_FILE, logger, setup_logger
from .handlers import WhitePathRichHandler

__all__ = [
    "DEFAULT_LOG_FILE",
    "WhitePathRichHandler",
    "logger",
    "setup_logger",
]
