"""
Summary: Share per-file processor state across helper functions.
Why: Reduce parameter churn while keeping dependencies explicit.
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
from ..ports import ArtistIdGeneratorPort, FilesystemPort


class ProcessorHooks(Protocol):
    """Minimal interface a processor must expose to helpers."""

    dry_run: bool
    artist_id_generator: ArtistIdGeneratorPort
    filesystem: FilesystemPort

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

    @property
    def filesystem(self) -> FilesystemPort:
        """Expose the filesystem port used by the active processor."""

        return self.processor.filesystem


__all__ = ["FileProcessingContext", "ProcessorHooks"]
