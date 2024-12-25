"""Centralized logging configuration for OMYM."""

import logging
import logging.handlers
import os
import re
from pathlib import Path
from typing import Optional, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text


class WhitePathRichHandler(RichHandler):
    """Custom Rich handler that displays file paths in white."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler with custom settings.

        Args:
            *args: Positional arguments to pass to RichHandler.
            **kwargs: Keyword arguments to pass to RichHandler.
        """
        kwargs["show_time"] = False
        kwargs["show_path"] = False
        kwargs["show_level"] = False  # We'll handle level display ourselves
        kwargs["rich_tracebacks"] = True
        kwargs["tracebacks_show_locals"] = True
        kwargs["markup"] = True
        kwargs["omit_repeated_times"] = False
        super().__init__(*args, **kwargs)

    def render_message(self, record: logging.LogRecord, message: str) -> Text:
        """Render message with white file paths.

        Args:
            record: Log record to format.
            message: Message to render.

        Returns:
            Rich Text object with formatted message.
        """
        text = Text()

        # Add level indicator with color
        if "Processing file:" in message:
            text.append("🔍 ", style=Style(color="blue", bold=True))
            message = message.replace("Processing file:", "")
            text.append("Processing:      ", style=Style(color="blue"))  # Fixed width with padding
        elif "File already processed:" in message:
            text.append("✓ ", style=Style(color="green", bold=True))
            message = message.replace("File already processed:", "")
            text.append(
                "Already processed:", style=Style(color="green")
            )  # Same width as "Processing:      "
        elif "Successfully committed" in message:
            text.append("💾 ", style=Style(color="green", bold=True))
            text.append(
                "Successfully committed all changes to database", style=Style(color="green")
            )
            return text
        elif "Configuration loaded" in message:
            text.append("⚙️  ", style=Style(color="cyan", bold=True))
            message = message.replace("Configuration loaded from", "")
            text.append("Configuration loaded from", style=Style(color="cyan"))
            text.append(" ")  # Add space after message
        elif record.levelno >= logging.ERROR:
            text.append("❌ ", style=Style(color="red", bold=True))
            text.append(message, style=Style(color="red"))
            return text
        elif record.levelno >= logging.WARNING:
            text.append("⚠️  ", style=Style(color="yellow", bold=True))
            text.append(message, style=Style(color="yellow"))
            return text
        else:
            text.append("ℹ️  ", style=Style(color="blue", bold=True))
            text.append(message, style=Style(color="blue"))
            return text

        # Match full paths first
        for match in re.finditer(r"(?:/[^/\s]+)+/?|[A-Za-z]:\\[^\s/\\]+(?:\\[^\s/\\]+)*", message):
            path = match.group(0)
            # Split path into components and separators
            if "\\" in path:  # Windows path
                parts = path.split("\\")
                for i, part in enumerate(parts):
                    if part:  # Skip empty parts
                        text.append(part, style=Style(color="bright_white"))
                        if i < len(parts) - 1:  # Add separator if not last part
                            text.append("\\", style=Style(color="magenta"))
            else:  # Unix path
                if path.startswith("/"):
                    text.append("/", style=Style(color="magenta"))  # Add initial slash with color
                parts = path.strip("/").split("/")
                for i, part in enumerate(parts):
                    if part:  # Skip empty parts
                        text.append(part, style=Style(color="bright_white"))
                        if i < len(parts) - 1:  # Add separator if not last part
                            text.append("/", style=Style(color="magenta"))
                if path.endswith("/"):
                    text.append("/", style=Style(color="magenta"))  # Add final slash with color

        return text


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

    # Remove any existing handlers
    logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler using Rich
    console = Console(force_terminal=True, soft_wrap=True)
    console_handler = WhitePathRichHandler(console=console)
    console_handler.setLevel(console_level)
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
