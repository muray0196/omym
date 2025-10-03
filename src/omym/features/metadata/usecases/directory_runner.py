"""src/omym/features/metadata/usecases/directory_runner.py
What: Shared implementation for directory-wide music processing.
Why: Keep MusicProcessor slim while reusing robust directory orchestration logic.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from omym.features.path.usecases.renamer import DirectoryGenerator, FileNameGenerator
from omym.platform.filesystem import remove_empty_directories

from .processing_types import (
    DirectoryRollbackError,
    ProcessResult,
    ProcessingEvent,
    ProcessingLogContext,
)
from .extraction.romanization import RomanizationCoordinator
from .extraction.track_metadata_extractor import MetadataExtractor
from .ports import DatabaseManagerPort
from omym.shared.track_metadata import TrackMetadata


class ProcessorLike(Protocol):
    """Subset of MusicProcessor needed for directory orchestration."""

    base_path: Path
    dry_run: bool
    db_manager: DatabaseManagerPort
    directory_generator: DirectoryGenerator
    SUPPORTED_EXTENSIONS: set[str]

    def log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: object,
    ) -> None:
        ...

    def process_file(
        self,
        file_path: Path,
        *,
        process_id: str | None = None,
        sequence: int | None = None,
        total: int | None = None,
        source_root: Path | None = None,
        target_root: Path | None = None,
        precomputed_metadata: TrackMetadata | None = None,
    ) -> ProcessResult:
        ...

    @property
    def romanization(self) -> RomanizationCoordinator:
        ...


def run_directory_processing(
    processor: ProcessorLike,
    directory: Path,
    progress_callback: Callable[[int, int, Path], None] | None = None,
) -> list[ProcessResult]:
    """Execute the directory processing loop shared by MusicProcessor."""

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    process_id = uuid.uuid4().hex[:12]
    results: list[ProcessResult] = []
    supported_files = [path for path in directory.rglob("*") if _is_supported(processor, path)]
    total_files = len(supported_files)

    if total_files == 0:
        processor.log_processing(
            logging.WARNING,
            ProcessingEvent.DIRECTORY_NO_FILES,
            "No supported music files found [id=%s, path=%s]",
            process_id,
            directory,
            process_id=process_id,
            directory=directory,
            total_files=0,
            dry_run=processor.dry_run,
            source_base_path=directory,
        )
        return results

    stats = ProcessingLogContext(
        process_id=process_id,
        directory=directory,
        total_files=total_files,
        dry_run=processor.dry_run,
    )
    processor.log_processing(
        logging.INFO,
        ProcessingEvent.DIRECTORY_START,
        "Directory processing started [id=%s, files=%d, dry_run=%s, path=%s]",
        process_id,
        total_files,
        processor.dry_run,
        directory,
        **stats.summary_extra(),
        source_base_path=directory,
    )

    precomputed_metadata: dict[Path, TrackMetadata] = {}
    for pre_file in supported_files:
        try:
            metadata = MetadataExtractor.extract(pre_file)
        except Exception:  # pragma: no cover - best effort pre-scan
            continue
        if metadata.artist:
            processor.romanization.ensure_scheduled(metadata.artist)
        if metadata.album_artist:
            processor.romanization.ensure_scheduled(metadata.album_artist)
        processor.directory_generator.register_album_year(metadata)
        FileNameGenerator.register_album_track_width(metadata)
        precomputed_metadata[pre_file] = metadata

    processed_count = 0
    conn = processor.db_manager.conn  # type: ignore[attr-defined]
    if conn is None:
        raise RuntimeError("Database connection is not initialized")

    try:
        if not processor.dry_run:
            _ = conn.execute("BEGIN TRANSACTION")

        for index, current_file in enumerate(supported_files, start=1):
            try:
                result = processor.process_file(
                    current_file,
                    process_id=process_id,
                    sequence=index,
                    total=total_files,
                    source_root=directory,
                    target_root=processor.base_path,
                    precomputed_metadata=precomputed_metadata.get(current_file),
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                error_message = str(exc) if str(exc) else type(exc).__name__
                stats.record_failure()
                processor.log_processing(
                    logging.ERROR,
                    ProcessingEvent.FILE_ERROR,
                    "Unhandled error processing file #%d/%d [id=%s, name=%s, error=%s]",
                    index,
                    total_files,
                    process_id,
                    current_file.name,
                    error_message,
                    process_id=process_id,
                    sequence=index,
                    total_files=total_files,
                    source_path=current_file,
                    source_base_path=directory,
                    error_message=error_message,
                )
                results.append(
                    ProcessResult(
                        source_path=current_file,
                        success=False,
                        error_message=error_message,
                        dry_run=processor.dry_run,
                    )
                )
                continue

            if result.skipped_duplicate:
                stats.record_skip()
                continue

            results.append(result)
            processed_count += 1

            if result.success:
                stats.record_success()
            else:
                stats.record_failure()

            if progress_callback:
                progress_callback(processed_count, total_files, current_file)

        if not processor.dry_run:
            remove_empty_directories(directory)
            conn.commit()

        summary_extra = stats.summary_extra()
        processor.log_processing(
            logging.INFO,
            ProcessingEvent.DIRECTORY_COMPLETE,
            "Directory processing completed [id=%s, processed=%d, skipped=%d, failed=%d, duration=%.2fs]",
            process_id,
            stats.processed,
            stats.skipped,
            stats.failed,
            summary_extra.get("duration_seconds", 0.0),
            **summary_extra,
            source_base_path=directory,
        )
    except Exception as exc:
        error_message = str(exc) if str(exc) else type(exc).__name__
        error_extra = stats.summary_extra()
        error_extra["error_message"] = error_message
        processor.log_processing(
            logging.ERROR,
            ProcessingEvent.DIRECTORY_ERROR,
            "Error processing directory [id=%s, path=%s, error=%s]",
            process_id,
            directory,
            error_message,
            **error_extra,
            source_base_path=directory,
        )
        if not processor.dry_run:
            try:
                conn.rollback()
            except sqlite3.Error as rollback_error:
                rollback_message = (
                    str(rollback_error)
                    if str(rollback_error)
                    else type(rollback_error).__name__
                )
                rollback_extra = stats.summary_extra()
                rollback_extra.update(
                    {
                        "error_message": error_message,
                        "rollback_error": rollback_message,
                    }
                )
                processor.log_processing(
                    logging.ERROR,
                    ProcessingEvent.DIRECTORY_ROLLBACK_ERROR,
                    "Database rollback failed after directory error [id=%s, path=%s, rollback_error=%s]",
                    process_id,
                    directory,
                    rollback_message,
                    **rollback_extra,
                    source_base_path=directory,
                )
                raise DirectoryRollbackError(
                    process_id=process_id,
                    directory=directory,
                    rollback_error=rollback_error,
                ) from rollback_error

    return results


def _is_supported(processor: ProcessorLike, file_path: Path) -> bool:
    return file_path.is_file() and file_path.suffix.lower() in processor.SUPPORTED_EXTENSIONS


__all__ = ["run_directory_processing"]
