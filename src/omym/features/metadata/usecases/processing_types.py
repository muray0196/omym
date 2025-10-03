"""src/omym/features/metadata/usecases/processing_types.py
Where: Metadata feature usecases layer.
What: Shared enums and dataclasses for music file processing flow.
Why: Keep the core processor lean by centralising type definitions.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from omym.shared.track_metadata import TrackMetadata


class ProcessingEvent(StrEnum):
    """Structured event identifiers for music file processing logs."""

    DIRECTORY_START = "processing.directory.start"
    DIRECTORY_COMPLETE = "processing.directory.complete"
    DIRECTORY_ERROR = "processing.directory.error"
    DIRECTORY_ROLLBACK_ERROR = "processing.directory.rollback_error"
    DIRECTORY_NO_FILES = "processing.directory.no_files"
    FILE_START = "processing.file.start"
    FILE_SKIP_DUPLICATE = "processing.file.skip.duplicate"
    FILE_ALREADY_ORGANIZED = "processing.file.already_organized"
    FILE_SUCCESS = "processing.file.success"
    FILE_ERROR = "processing.file.error"
    FILE_MOVE = "processing.file.move"
    LYRICS_MOVE = "processing.lyrics.move"
    LYRICS_PLAN = "processing.lyrics.plan"
    LYRICS_SKIP_MISSING = "processing.lyrics.skip.missing"
    LYRICS_SKIP_CONFLICT = "processing.lyrics.skip.conflict"
    LYRICS_SKIP_ALREADY_AT_TARGET = "processing.lyrics.skip.already_at_target"
    LYRICS_ERROR = "processing.lyrics.error"
    ARTWORK_MOVE = "processing.artwork.move"
    ARTWORK_PLAN = "processing.artwork.plan"
    ARTWORK_SKIP_MISSING = "processing.artwork.skip.missing"
    ARTWORK_SKIP_CONFLICT = "processing.artwork.skip.conflict"
    ARTWORK_SKIP_ALREADY_AT_TARGET = "processing.artwork.skip.already_at_target"
    ARTWORK_SKIP_NO_TARGET = "processing.artwork.skip.no_target"
    ARTWORK_ERROR = "processing.artwork.error"


@dataclass(slots=True)
class ProcessingLogContext:
    """Mutable bookkeeping for a directory processing run."""

    process_id: str
    directory: Path
    total_files: int
    dry_run: bool
    start_time: float = field(default_factory=time.perf_counter)
    processed: int = 0
    skipped: int = 0
    failed: int = 0

    def record_success(self) -> None:
        """Increment the counter of successfully processed files."""

        self.processed += 1

    def record_skip(self) -> None:
        """Increment the counter of skipped files."""

        self.skipped += 1

    def record_failure(self) -> None:
        """Increment the counter of failed files."""

        self.failed += 1

    def duration_seconds(self) -> float:
        """Return the elapsed processing time in seconds."""

        return time.perf_counter() - self.start_time

    def summary_extra(self) -> dict[str, Any]:
        """Return a dictionary suitable for structured logging extras."""

        return {
            "process_id": self.process_id,
            "directory": str(self.directory),
            "total_files": self.total_files,
            "processed": self.processed,
            "skipped": self.skipped,
            "failed": self.failed,
            "dry_run": self.dry_run,
            "duration_seconds": round(self.duration_seconds(), 4),
        }


class DirectoryRollbackError(RuntimeError):
    """Raised when rolling back a directory processing transaction fails."""

    def __init__(self, process_id: str, directory: Path, rollback_error: sqlite3.Error) -> None:
        message = (
            "Database rollback failed for directory processing "
            f"(process_id={process_id}, directory={directory}): {rollback_error}"
        )
        super().__init__(message)
        self.process_id: str = process_id
        self.directory: Path = directory
        self.rollback_error: sqlite3.Error = rollback_error


@dataclass
class LyricsProcessingResult:
    """Outcome of processing an associated lyrics (.lrc) file."""

    source_path: Path
    target_path: Path
    moved: bool
    dry_run: bool
    reason: str | None = None


@dataclass
class ArtworkProcessingResult:
    """Outcome of processing artwork assets that accompany a track."""

    source_path: Path
    target_path: Path
    linked_track: Path | None
    moved: bool
    dry_run: bool
    reason: str | None = None


@dataclass
class ProcessResult:
    """Result of processing a music file."""

    source_path: Path
    target_path: Path | None = None
    success: bool = False
    error_message: str | None = None
    dry_run: bool = False
    file_hash: str | None = None
    metadata: TrackMetadata | None = None
    artist_id: str | None = None
    lyrics_result: LyricsProcessingResult | None = None
    artwork_results: list[ArtworkProcessingResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_duplicate: bool = False


__all__ = [
    "ProcessingEvent",
    "ProcessingLogContext",
    "DirectoryRollbackError",
    "ProcessResult",
    "LyricsProcessingResult",
    "ArtworkProcessingResult",
]
