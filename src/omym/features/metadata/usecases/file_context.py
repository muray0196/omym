"""src/omym/features/metadata/usecases/file_context.py
What: Shared state container for per-file processing helpers.
Why: Avoid long parameter lists when coordinating helper functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .processing_types import (
    ArtworkProcessingResult,
    LyricsProcessingResult,
    ProcessingEvent,
)


class ProcessorHooks(Protocol):
    """Minimal interface a processor must expose to helpers."""

    dry_run: bool

    def log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: object,
    ) -> None:
        ...


@dataclass
class FileProcessingContext:
    """State shared across file-processing helper functions."""

    processor: ProcessorHooks
    file_path: Path
    process_id: str
    sequence: int | None
    total: int | None
    source_root: Path
    target_root: Path
    file_hash: str | None = None
    warnings: list[str] = field(default_factory=list)
    lyrics_result: LyricsProcessingResult | None = None
    artwork_results: list[ArtworkProcessingResult] = field(default_factory=list)


__all__ = ["FileProcessingContext", "ProcessorHooks"]
