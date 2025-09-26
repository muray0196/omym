"""src/omym/features/metadata/usecases/file_runner.py
What: Shared implementation for per-file music processing.
Why: Shrink MusicProcessor by factoring out procedural logic.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Protocol

from omym.features.path.usecases.renamer import DirectoryGenerator, FileNameGenerator

from .asset_detection import find_associated_lyrics, resolve_directory_artwork
from .file_context import FileProcessingContext
from .file_duplicate import handle_duplicate
from .file_success import complete_success
from .ports import ArtistCachePort, ProcessingAfterPort, ProcessingBeforePort
from .processing_types import ProcessResult, ProcessingEvent
from .romanization import RomanizationCoordinator
from .track_metadata_extractor import MetadataExtractor
from ..domain.track_metadata import TrackMetadata


class ProcessorLike(Protocol):
    """Subset of MusicProcessor needed for per-file orchestration."""

    dry_run: bool
    base_path: Path
    before_dao: ProcessingBeforePort
    after_dao: ProcessingAfterPort
    artist_dao: ArtistCachePort
    directory_generator: DirectoryGenerator
    file_name_generator: FileNameGenerator
    SUPPORTED_EXTENSIONS: set[str]
    SUPPORTED_IMAGE_EXTENSIONS: set[str]

    def _calculate_file_hash(self, file_path: Path) -> str:
        ...

    def calculate_file_hash(self, file_path: Path) -> str:
        ...

    def _generate_target_path(
        self,
        metadata: TrackMetadata,
        *,
        existing_path: Path | None = None,
    ) -> Path | None:
        ...

    def generate_target_path(
        self,
        metadata: TrackMetadata,
        *,
        existing_path: Path | None = None,
    ) -> Path | None:
        ...

    def _move_file(
        self,
        src_path: Path,
        dest_path: Path,
        *,
        process_id: str | None = None,
        sequence: int | None = None,
        total: int | None = None,
        source_root: Path | None = None,
        target_root: Path | None = None,
    ) -> None:
        ...

    def move_file(
        self,
        src_path: Path,
        dest_path: Path,
        *,
        process_id: str | None = None,
        sequence: int | None = None,
        total: int | None = None,
        source_root: Path | None = None,
        target_root: Path | None = None,
    ) -> None:
        ...

    def log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: object,
    ) -> None:
        ...

    @property
    def romanization(self) -> RomanizationCoordinator:
        ...


def run_file_processing(
    processor: ProcessorLike,
    file_path: Path,
    *,
    process_id: str | None = None,
    sequence: int | None = None,
    total: int | None = None,
    source_root: Path | None = None,
    target_root: Path | None = None,
) -> ProcessResult:
    start_time = time.perf_counter()
    current_process_id = process_id or uuid.uuid4().hex[:12]
    effective_source_root = source_root or file_path.parent
    effective_target_root = target_root or processor.base_path

    ctx = FileProcessingContext(
        processor=processor,
        file_path=file_path,
        process_id=current_process_id,
        sequence=sequence,
        total=total,
        source_root=effective_source_root,
        target_root=effective_target_root,
        warnings=[],
        lyrics_result=None,
        artwork_results=[],
    )

    associated_lyrics, detection_warnings = find_associated_lyrics(file_path)
    if detection_warnings:
        ctx.warnings.extend(detection_warnings)

    artwork_candidates, is_primary_track = resolve_directory_artwork(
        file_path,
        supported_track_extensions=processor.SUPPORTED_EXTENSIONS,
        supported_image_extensions=processor.SUPPORTED_IMAGE_EXTENSIONS,
    )
    associated_artwork = artwork_candidates if is_primary_track else []

    try:
        ctx.file_hash = processor.calculate_file_hash(file_path)
        processor.log_processing(
            logging.DEBUG,
            ProcessingEvent.FILE_START,
            "Processing file [id=%s, name=%s, hash=%s, dry_run=%s]",
            ctx.process_id,
            file_path.name,
            ctx.file_hash,
            processor.dry_run,
            process_id=ctx.process_id,
            sequence=sequence,
            total_files=total,
            source_path=file_path,
            source_base_path=effective_source_root,
            file_hash=ctx.file_hash,
            dry_run=processor.dry_run,
        )

        if processor.before_dao.check_file_exists(ctx.file_hash):
            target_raw = processor.before_dao.get_target_path(ctx.file_hash)
            return handle_duplicate(
                ctx,
                target_raw=target_raw,
                associated_lyrics=associated_lyrics,
                associated_artwork=associated_artwork,
            )

        metadata = MetadataExtractor.extract(file_path)
        if not metadata:
            raise ValueError("Failed to extract metadata")

        if metadata.artist:
            processor.romanization.ensure_scheduled(metadata.artist)
            metadata.artist = processor.romanization.await_result(metadata.artist)
        if metadata.album_artist:
            processor.romanization.ensure_scheduled(metadata.album_artist)
            metadata.album_artist = processor.romanization.await_result(metadata.album_artist)

        target_path = processor.generate_target_path(metadata, existing_path=file_path)
        if not target_path:
            raise ValueError("Failed to generate target path")

        if not processor.dry_run:
            if not processor.before_dao.insert_file(ctx.file_hash, file_path):
                raise ValueError("Failed to save file state to database")

        if not processor.dry_run:
            processor.move_file(
                file_path,
                target_path,
                process_id=ctx.process_id,
                sequence=sequence,
                total=total,
                source_root=effective_source_root,
                target_root=effective_target_root,
            )
            if not processor.after_dao.insert_file(ctx.file_hash, file_path, target_path):
                raise ValueError("Failed to save file state to database")

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return complete_success(
            ctx,
            target_path=target_path,
            metadata=metadata,
            associated_lyrics=associated_lyrics,
            associated_artwork=associated_artwork,
            duration_ms=duration_ms,
        )

    except Exception as exc:
        error_message = str(exc) if str(exc) else type(exc).__name__
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        processor.log_processing(
            logging.ERROR,
            ProcessingEvent.FILE_ERROR,
            "Error processing file [id=%s, name=%s, error=%s, duration_ms=%.2f]",
            ctx.process_id,
            file_path.name,
            error_message,
            duration_ms,
            process_id=ctx.process_id,
            sequence=sequence,
            total_files=total,
            source_path=file_path,
            source_base_path=effective_source_root,
            file_hash=ctx.file_hash,
            error_message=error_message,
            duration_ms=duration_ms,
            dry_run=processor.dry_run,
        )
        return ProcessResult(
            source_path=file_path,
            success=False,
            error_message=error_message,
            dry_run=processor.dry_run,
            file_hash=ctx.file_hash,
            artwork_results=ctx.artwork_results,
            warnings=ctx.warnings,
        )


__all__ = ["run_file_processing"]
