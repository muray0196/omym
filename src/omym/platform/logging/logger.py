"""Centralized logging configuration for OMYM."""

import logging
import logging.handlers
import os
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, ClassVar, override
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text

from omym.config.paths import default_log_file


class WhitePathRichHandler(RichHandler):
    """Custom Rich handler that displays file paths in white."""

    _PROCESSING_STYLES: ClassVar[dict[str, tuple[str, str]]] = {
        "processing.directory.start": ("🚀", "cyan"),
        "processing.directory.complete": ("✅", "green"),
        "processing.directory.error": ("❌", "red"),
        "processing.directory.no_files": ("ℹ️", "yellow"),
        "processing.file.start": ("🎧", "blue"),
        "processing.file.success": ("🎉", "green"),
        "processing.file.skip.duplicate": ("↪️", "yellow"),
        "processing.file.error": ("⛔", "red"),
        "processing.file.move": ("📦", "magenta"),
    }
    _PATH_SEGMENT_LIMIT: ClassVar[int] = 4

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

    def _format_path(self, path: str, base: str | None = None) -> Text:
        """Format a path with colored separators and compact rendering.

        Args:
            path: Absolute or relative path string to format.
            base: Optional base path used to relativize ``path`` when possible.

        Returns:
            Text: Formatted path with colored separators and ellipsis truncation.
        """
        pure_path = self._to_pure_path(path)
        base_path = self._to_pure_path(base) if base else None

        display_path: PurePath = pure_path
        if base_path is not None and self._is_relative_to(pure_path, base_path):
            relative_path = pure_path.relative_to(base_path)
            if str(relative_path) not in {"", "."}:
                display_path = relative_path

        separator = "\\" if isinstance(display_path, PureWindowsPath) else "/"
        anchor = display_path.anchor
        body_parts = [part for part in display_path.parts if part and part != anchor]

        truncated = len(body_parts) > self._PATH_SEGMENT_LIMIT
        if truncated:
            body_parts = body_parts[-self._PATH_SEGMENT_LIMIT:]

        display_string = self._build_display_string(
            anchor=anchor,
            body_parts=body_parts,
            separator=separator,
            truncated=truncated,
            is_windows=isinstance(display_path, PureWindowsPath),
        )
        return self._style_path_string(display_string, separator)

    @staticmethod
    def _to_pure_path(raw_path: str) -> PurePath:
        """Return a platform-aware ``PurePath`` for the given raw string."""

        if "\\" in raw_path:
            return PureWindowsPath(raw_path)
        return PurePosixPath(raw_path)

    @staticmethod
    def _is_relative_to(path: PurePath, other: PurePath) -> bool:
        """Return whether ``path`` can be expressed relative to ``other``."""

        try:
            _ = path.relative_to(other)
            return True
        except ValueError:
            return False

    def _build_display_string(
        self,
        *,
        anchor: str,
        body_parts: list[str],
        separator: str,
        truncated: bool,
        is_windows: bool,
    ) -> str:
        """Build a compact string representation of the path."""

        display_string = ""
        if anchor:
            if is_windows:
                display_string = anchor.rstrip("\\/")
                if truncated or body_parts:
                    display_string += separator
                elif not display_string.endswith(separator):
                    display_string += separator
            else:
                display_string = separator

        if truncated:
            display_string += "…"
            if body_parts:
                display_string += separator

        if body_parts:
            display_string += separator.join(body_parts)

        if not display_string:
            return "."
        return display_string

    @staticmethod
    def _style_path_string(path_string: str, separator: str) -> Text:
        """Apply Rich styling to the rendered path string."""

        text = Text()
        separator_chars = {separator}
        if separator == "\\":
            separator_chars.add("/")

        for char in path_string:
            if char in separator_chars or char == "…":
                _ = text.append(char, style=Style(color="magenta"))
            else:
                _ = text.append(char, style=Style(color="white"))
        return text

    def _render_processing_message(self, record: logging.LogRecord) -> Text | None:
        """Render structured processing events with dedicated styling."""

        event = getattr(record, "processing_event", None)
        if not isinstance(event, str):
            return None

        icon, color = self._PROCESSING_STYLES.get(event, ("ℹ️", "blue"))
        text = Text()

        icon_style = Style(color=color, bold=True)
        _ = text.append(f"{icon} ", style=icon_style)

        body = Text(style=Style(color=color))

        if event.startswith("processing.directory"):
            directory = getattr(record, "directory", None)
            if event == "processing.directory.start":
                total_files = getattr(record, "total_files", None)
                dry_run = getattr(record, "dry_run", None)
                _ = body.append("Directory start")
                details: list[str] = []
                if isinstance(total_files, int):
                    details.append(f"total={total_files}")
                if dry_run:
                    details.append("dry-run")
                if details:
                    _ = body.append(" [" + ", ".join(details) + "]")
            elif event == "processing.directory.complete":
                processed = getattr(record, "processed", None)
                skipped = getattr(record, "skipped", None)
                failed = getattr(record, "failed", None)
                duration = getattr(record, "duration_seconds", None)
                _ = body.append("Directory complete")
                directory_metrics: list[str] = []
                if isinstance(processed, int):
                    directory_metrics.append(f"processed={processed}")
                if isinstance(skipped, int):
                    directory_metrics.append(f"skipped={skipped}")
                if isinstance(failed, int):
                    directory_metrics.append(f"failed={failed}")
                if isinstance(duration, (int, float)):
                    directory_metrics.append(f"duration={duration:.2f}s")
                if directory_metrics:
                    _ = body.append(" [" + ", ".join(directory_metrics) + "]")
            elif event == "processing.directory.no_files":
                _ = body.append("No supported files")
            else:
                error = getattr(record, "error_message", None)
                _ = body.append("Directory error")
                if error:
                    _ = body.append(f" ({error})")
            if directory:
                _ = body.append(" @ ")
                _ = body.append_text(
                    self._format_path(
                        str(directory),
                        base=getattr(record, "source_base_path", None),
                    )
                )
        else:
            sequence = getattr(record, "sequence", None)
            total_files = getattr(record, "total_files", None)
            if isinstance(sequence, int) and sequence > 0:
                if isinstance(total_files, int) and total_files > 0:
                    _ = body.append(f"[{sequence}/{total_files}] ")
                else:
                    _ = body.append(f"[{sequence}] ")

            prefix = {
                "processing.file.start": "Processing ",
                "processing.file.success": "Processed ",
                "processing.file.skip.duplicate": "Skipped duplicate ",
                "processing.file.error": "Failed ",
                "processing.file.move": "Moving ",
            }.get(event)
            if prefix:
                _ = body.append(prefix)

            source_path = getattr(record, "source_path", None)
            target_path = getattr(record, "target_path", None)
            source_base_path = getattr(record, "source_base_path", None)
            target_base_path = getattr(record, "target_base_path", None)
            if source_path:
                _ = body.append_text(
                    self._format_path(str(source_path), base=source_base_path)
                )

            if event in {
                "processing.file.success",
                "processing.file.move",
                "processing.file.skip.duplicate",
            } and target_path:
                _ = body.append(" → ")
                _ = body.append_text(
                    self._format_path(str(target_path), base=target_base_path)
                )

            file_metrics: list[str] = []
            if event == "processing.file.success":
                duration_ms = getattr(record, "duration_ms", None)
                if isinstance(duration_ms, (int, float)):
                    file_metrics.append(f"{duration_ms:.2f} ms")
                artist = getattr(record, "artist", None)
                title = getattr(record, "title", None)
                label = " - ".join(part for part in [artist, title] if part)
                if label:
                    file_metrics.append(label)
            elif event == "processing.file.error":
                error_message = getattr(record, "error_message", None)
                if error_message:
                    file_metrics.append(str(error_message))
            if file_metrics:
                _ = body.append(" (" + ", ".join(file_metrics) + ")")

        _ = text.append_text(body)
        return text

    def _render_musicbrainz_message(self, message: str) -> Text | None:
        """Render MusicBrainz romanization messages with consistent styling."""

        if "MusicBrainz romanized" not in message:
            return None

        is_cached = message.startswith("Using cached MusicBrainz romanized")
        icon = "♻️" if is_cached else "ℹ️"
        color = "green" if is_cached else "blue"

        text = Text()
        _ = text.append(f"{icon} ", style=Style(color=color, bold=True))
        _ = text.append(message, style=Style(color=color))
        return text

    @override
    def render_message(self, record: logging.LogRecord, message: str) -> ConsoleRenderable:
        """Render message with custom styling for processing events."""

        processing_text = self._render_processing_message(record)
        if processing_text is not None:
            return processing_text

        musicbrainz_text = self._render_musicbrainz_message(message)
        if musicbrainz_text is not None:
            return musicbrainz_text

        return super().render_message(record, message)


DEFAULT_LOG_FILE: Path = default_log_file()


def setup_logger(
    log_file: Path | None = None,
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

    # Remove any existing handlers cleanly
    for handler in list(logger.handlers):
        handler.close()
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
        resolved_log_file = Path(log_file).expanduser().resolve()
        os.makedirs(resolved_log_file.parent, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            resolved_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger(log_file=DEFAULT_LOG_FILE)
