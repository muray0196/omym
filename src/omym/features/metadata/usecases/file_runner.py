# /*
# Where: features/metadata/usecases/file_runner.py
# What: Shared implementation for per-file music processing orchestration.
# Why: Keep MusicProcessor lean by isolating procedural flow and duplicate handling.
# Assumptions:
# - Processor dependencies follow ports specified in features.metadata.usecases.ports.
# - File system semantics follow pathlib/shutil guarantees on POSIX-like systems.
# Trade-offs:
# - Duplicate detection now defers until metadata extraction to permit reorganizing when targets shift.
# - Additional filesystem comparisons introduce minor overhead but improve correctness.
# */

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from dataclasses import asdict
from typing import Any, Protocol, cast

from omym.features.path.usecases.renamer import (
    CachedArtistIdGenerator,
    DirectoryGenerator,
    FileNameGenerator,
)

from .asset_detection import find_associated_lyrics, resolve_directory_artwork
from .file_context import FileProcessingContext
from .file_duplicate import handle_duplicate
from .file_success import complete_success
from .ports import (
    ArtistCachePort,
    PreviewCachePort,
    ProcessingAfterPort,
    ProcessingBeforePort,
)
from .processing_types import ProcessResult, ProcessingEvent
from .extraction.romanization import RomanizationCoordinator
from .extraction.track_metadata_extractor import MetadataExtractor
from ..domain.track_metadata import TrackMetadata


LOGGER = logging.getLogger(__name__)


def _paths_point_to_same_file(first: Path, second: Path) -> bool:
    """Return True when two paths refer to the same filesystem entity."""

    try:
        return first.samefile(second)
    except (FileNotFoundError, OSError):
        return first.resolve() == second.resolve()


class ProcessorLike(Protocol):
    """Subset of MusicProcessor needed for per-file orchestration."""

    dry_run: bool
    base_path: Path
    before_dao: ProcessingBeforePort
    after_dao: ProcessingAfterPort
    artist_dao: ArtistCachePort
    preview_dao: PreviewCachePort
    artist_id_generator: CachedArtistIdGenerator
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

        duplicate_target_path: Path | None = None
        if processor.before_dao.check_file_exists(ctx.file_hash):
            target_raw = processor.before_dao.get_target_path(ctx.file_hash)
            if target_raw is not None:
                duplicate_target_path = Path(target_raw)

        preview_entry = None
        preview_used = False
        preview_payload: dict[str, object] = {}
        if not processor.dry_run:
            preview_entry = processor.preview_dao.get_preview(ctx.file_hash)
            if preview_entry is not None:
                source_matches = str(preview_entry.source_path) == str(file_path)
                base_matches = str(preview_entry.base_path) == str(processor.base_path)
                if source_matches and base_matches:
                    preview_payload = preview_entry.payload
                    preview_used = True

        metadata: TrackMetadata | None = None
        original_artist: str | None = None
        original_album_artist: str | None = None

        if preview_used:
            maybe_metadata = preview_payload.get("metadata")
            if isinstance(maybe_metadata, dict):
                metadata_dict = cast(dict[str, object], maybe_metadata)
                metadata = _metadata_from_payload(metadata_dict)
            raw_original_artist = preview_payload.get("original_artist")
            if isinstance(raw_original_artist, str):
                original_artist = raw_original_artist
            raw_original_album_artist = preview_payload.get("original_album_artist")
            if isinstance(raw_original_album_artist, str):
                original_album_artist = raw_original_album_artist

        if metadata is None:
            raw_metadata = cast(Any, MetadataExtractor.extract(file_path))
            if raw_metadata is None:  # Defensive for mocked extractors in tests.
                raise ValueError("Failed to extract metadata")
            metadata = cast(TrackMetadata, raw_metadata)

            original_artist = metadata.artist
            original_album_artist = metadata.album_artist

            if metadata.artist:
                processor.romanization.ensure_scheduled(metadata.artist)
                metadata.artist = processor.romanization.await_result(metadata.artist)
            if metadata.album_artist:
                processor.romanization.ensure_scheduled(metadata.album_artist)
                metadata.album_artist = processor.romanization.await_result(metadata.album_artist)

        target_path = processor.generate_target_path(metadata, existing_path=file_path)
        if not target_path:
            raise ValueError("Failed to generate target path")

        # Defer duplicate checks until after recomputing the destination so reorganize runs
        # can relocate tracks when artist IDs or metadata evolve.
        if duplicate_target_path is not None and _paths_point_to_same_file(
            duplicate_target_path, target_path
        ):
            return handle_duplicate(
                ctx,
                target_raw=duplicate_target_path,
                associated_lyrics=associated_lyrics,
                associated_artwork=associated_artwork,
            )

        if preview_used and not processor.dry_run:
            _sync_preview_romanization(
                processor,
                original_artist,
                metadata.artist,
            )
            _sync_preview_romanization(
                processor,
                original_album_artist,
                metadata.album_artist,
            )

        if processor.dry_run:
            payload: dict[str, object] = {
                "metadata": asdict(metadata),
                "original_artist": original_artist or "",
                "original_album_artist": original_album_artist or "",
            }
            _ = processor.preview_dao.upsert_preview(
                file_hash=ctx.file_hash,
                source_path=file_path.resolve(),
                base_path=processor.base_path.resolve(),
                target_path=target_path,
                payload=payload,
            )

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
        result = complete_success(
            ctx,
            target_path=target_path,
            metadata=metadata,
            associated_lyrics=associated_lyrics,
            associated_artwork=associated_artwork,
            duration_ms=duration_ms,
        )
        if not processor.dry_run and preview_used and result.success:
            _ = processor.preview_dao.delete_preview(ctx.file_hash)
        return result

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


def _metadata_from_payload(raw: dict[str, object]) -> TrackMetadata:
    """Reconstruct metadata objects from cached payloads."""

    return TrackMetadata(
        title=cast(str | None, raw.get("title")),
        artist=cast(str | None, raw.get("artist")),
        album=cast(str | None, raw.get("album")),
        album_artist=cast(str | None, raw.get("album_artist")),
        genre=cast(str | None, raw.get("genre")),
        year=cast(int | None, raw.get("year")),
        track_number=cast(int | None, raw.get("track_number")),
        track_total=cast(int | None, raw.get("track_total")),
        disc_number=cast(int | None, raw.get("disc_number")),
        disc_total=cast(int | None, raw.get("disc_total")),
        file_extension=cast(str | None, raw.get("file_extension")),
    )


def _sync_preview_romanization(
    processor: ProcessorLike,
    original_name: str | None,
    romanized_name: str | None,
) -> None:
    """Persist romanized names collected during dry runs."""

    if not original_name or not romanized_name:
        return

    normalized_original = original_name.strip()
    normalized_romanized = romanized_name.strip()
    if not normalized_original or not normalized_romanized:
        return
    if normalized_original == normalized_romanized:
        return

    try:
        _ = processor.artist_dao.upsert_romanized_name(
            normalized_original,
            normalized_romanized,
            source=None,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning(
            "Failed to persist romanized name for '%s': %s",
            normalized_original,
            exc,
        )


__all__ = ["run_file_processing"]
