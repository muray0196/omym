"""Process music files for organization."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, ClassVar, final

from omym.domain.metadata.artist_romanizer import ArtistRomanizer
from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.metadata.track_metadata_extractor import MetadataExtractor
from omym.domain.path.music_file_renamer import (
    DirectoryGenerator,
    FileNameGenerator,
    CachedArtistIdGenerator,
)
from omym.infra.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.infra.db.daos.processing_after_dao import ProcessingAfterDAO
from omym.infra.db.daos.processing_before_dao import ProcessingBeforeDAO
from omym.infra.db.db_manager import DatabaseManager
from omym.infra.logger.logger import logger
from omym.infra.musicbrainz.client import (
    configure_romanization_cache,
    fetch_romanized_name,
)




class ProcessingEvent(StrEnum):
    """Structured event identifiers for music file processing logs."""

    DIRECTORY_START = "processing.directory.start"
    DIRECTORY_COMPLETE = "processing.directory.complete"
    DIRECTORY_ERROR = "processing.directory.error"
    DIRECTORY_NO_FILES = "processing.directory.no_files"
    FILE_START = "processing.file.start"
    FILE_SKIP_DUPLICATE = "processing.file.skip.duplicate"
    FILE_SUCCESS = "processing.file.success"
    FILE_ERROR = "processing.file.error"
    FILE_MOVE = "processing.file.move"
    LYRICS_MOVE = "processing.lyrics.move"
    LYRICS_PLAN = "processing.lyrics.plan"
    LYRICS_SKIP_MISSING = "processing.lyrics.skip.missing"
    LYRICS_SKIP_CONFLICT = "processing.lyrics.skip.conflict"
    LYRICS_ERROR = "processing.lyrics.error"


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
    warnings: list[str] = field(default_factory=list)


@dataclass
class LyricsProcessingResult:
    """Outcome of processing an associated lyrics (.lrc) file."""

    source_path: Path
    target_path: Path
    moved: bool
    dry_run: bool
    reason: str | None = None


@final
class MusicProcessor:
    """Process music files for organization."""

    # Supported file extensions.
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".mp3", ".flac", ".m4a", ".dsf", ".aac", ".alac", ".opus"}

    base_path: Path
    dry_run: bool
    db_manager: DatabaseManager
    before_dao: ProcessingBeforeDAO
    after_dao: ProcessingAfterDAO
    artist_dao: ArtistCacheDAO
    artist_id_generator: CachedArtistIdGenerator
    directory_generator: DirectoryGenerator
    file_name_generator: FileNameGenerator
    _romanizer: ArtistRomanizer
    _romanizer_executor: ThreadPoolExecutor
    _romanize_futures: dict[str, Future[str]]

    def __init__(self, base_path: Path, dry_run: bool = False) -> None:
        """Initialize music processor.

        Args:
            base_path: Base path for organizing music files.
            dry_run: Whether to perform a dry run (no actual file operations).
        """
        self.base_path = base_path
        self.dry_run = dry_run

        # Initialize database connection.
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        if self.db_manager.conn is None:
            raise RuntimeError("Failed to connect to database")

        # Initialize DAOs.
        self.before_dao = ProcessingBeforeDAO(self.db_manager.conn)
        self.after_dao = ProcessingAfterDAO(self.db_manager.conn)
        self.artist_dao = ArtistCacheDAO(self.db_manager.conn)
        configure_romanization_cache(self.artist_dao)

        def _fetch_with_persistent_cache(name: str) -> str | None:
            trimmed = name.strip()
            if not trimmed:
                return None

            try:
                cached = self.artist_dao.get_romanized_name(trimmed)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to consult persistent romanization cache for '%s': %s",
                    trimmed,
                    exc,
                )
                cached = None

            if cached:
                if hasattr(self, "_romanizer"):
                    self._romanizer.record_fetch_context(
                        source="cache",
                        original=trimmed,
                        value=cached,
                    )
                return cached

            result = fetch_romanized_name(name)
            if hasattr(self, "_romanizer"):
                self._romanizer.record_fetch_context(
                    source="musicbrainz",
                    original=trimmed,
                    value=result,
                )
            return result

        # Initialize generators.
        self.artist_id_generator = CachedArtistIdGenerator(self.artist_dao)
        self.directory_generator = DirectoryGenerator()
        self.file_name_generator = FileNameGenerator(self.artist_id_generator)
        self._romanizer = ArtistRomanizer(fetcher=_fetch_with_persistent_cache)
        MetadataExtractor.configure_romanizer(self._romanizer)
        self._romanizer_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mb-romanizer")
        self._romanize_futures = {}

    def _log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: Any,
    ) -> None:
        """Emit a structured log entry for processing operations."""

        extra: dict[str, Any] = {"processing_event": event.value}
        for key, value in context.items():
            if isinstance(value, Path):
                extra[key] = str(value)
            else:
                extra[key] = value
        logger.log(level, message, *message_args, extra=extra, stacklevel=2)

    def process_directory(
        self,
        directory: Path,
        progress_callback: Callable[[int, int, Path], None] | None = None,
    ) -> list[ProcessResult]:
        """Process all music files in a directory.

        Args:
            directory: Directory to process.
            progress_callback: Optional callback for progress updates. Signature:
                (processed_count, total_count, current_file_path)

        Returns:
            List of ProcessResult objects.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        process_id = uuid.uuid4().hex[:12]
        results: list[ProcessResult] = []
        supported_files = [f for f in directory.rglob("*") if self._is_supported(f)]
        total_files = len(supported_files)

        if total_files == 0:
            self._log_processing(
                logging.WARNING,
                ProcessingEvent.DIRECTORY_NO_FILES,
                "No supported music files found [id=%s, path=%s]",
                process_id,
                directory,
                process_id=process_id,
                directory=directory,
                total_files=0,
                dry_run=self.dry_run,
                source_base_path=directory,
            )
            return results

        stats = ProcessingLogContext(
            process_id=process_id,
            directory=directory,
            total_files=total_files,
            dry_run=self.dry_run,
        )
        self._log_processing(
            logging.INFO,
            ProcessingEvent.DIRECTORY_START,
            "Directory processing started [id=%s, files=%d, dry_run=%s, path=%s]",
            process_id,
            total_files,
            self.dry_run,
            directory,
            **stats.summary_extra(),
            source_base_path=directory,
        )

        # Pre-scan metadata to register album years across the whole directory.
        # This ensures the album-level earliest year is known before generating any paths,
        # avoiding transient splits like 2020_/2024_ for the same album based on processing order.
        for pre_file in supported_files:
            try:
                meta = MetadataExtractor.extract(pre_file)
                if meta.artist:
                    self._schedule_romanization(meta.artist)
                if meta.album_artist:
                    self._schedule_romanization(meta.album_artist)
                self.directory_generator.register_album_year(meta)
                # Register album-level track width for consistent padding
                FileNameGenerator.register_album_track_width(meta)
            except Exception:
                # Best-effort: failure to read one file's metadata must not block processing
                continue

        processed_count = 0
        try:
            conn = self.db_manager.conn
            if conn is None:
                raise RuntimeError("Database connection is not initialized")
            _ = conn.execute("BEGIN TRANSACTION")

            for index, current_file in enumerate(supported_files, start=1):
                try:
                    file_hash = self._calculate_file_hash(current_file)
                    if self.before_dao.check_file_exists(file_hash):
                        target_path: Path | None = None
                        try:
                            target_raw = self.before_dao.get_target_path(file_hash)
                            target_path = Path(target_raw) if target_raw else None
                        except Exception:
                            target_path = None

                        stats.record_skip()
                        self._log_processing(
                            logging.INFO,
                            ProcessingEvent.FILE_SKIP_DUPLICATE,
                            "Skipping already-processed file #%d/%d [id=%s, name=%s, target=%s]",
                            index,
                            total_files,
                            process_id,
                            current_file.name,
                            target_path or "<unknown>",
                            process_id=process_id,
                            sequence=index,
                            total_files=total_files,
                            source_path=current_file,
                            source_base_path=directory,
                            target_path=target_path,
                            target_base_path=self.base_path,
                            file_hash=file_hash,
                        )
                        continue

                    result = self.process_file(
                        current_file,
                        process_id=process_id,
                        sequence=index,
                        total=total_files,
                        source_root=directory,
                        target_root=self.base_path,
                    )
                except Exception as exc:
                    error_message = str(exc) if str(exc) else type(exc).__name__
                    stats.record_failure()
                    self._log_processing(
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
                            dry_run=self.dry_run,
                        )
                    )
                    continue

                results.append(result)
                processed_count += 1

                if result.success:
                    stats.record_success()
                else:
                    stats.record_failure()

                if progress_callback:
                    progress_callback(processed_count, total_files, current_file)

            if not self.dry_run:
                self._cleanup_empty_directories(directory)

            conn = self.db_manager.conn
            if conn is None:
                raise RuntimeError("Database connection is not initialized")
            conn.commit()

            summary_extra = stats.summary_extra()
            self._log_processing(
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
            self._log_processing(
                logging.ERROR,
                ProcessingEvent.DIRECTORY_ERROR,
                "Error processing directory [id=%s, path=%s, error=%s]",
                process_id,
                directory,
                error_message,
                **error_extra,
                source_base_path=directory,
            )
            conn = self.db_manager.conn
            if conn is not None:
                conn.rollback()

        return results

    def process_file(
        self,
        file_path: Path,
        *,
        process_id: str | None = None,
        sequence: int | None = None,
        total: int | None = None,
        source_root: Path | None = None,
        target_root: Path | None = None,
    ) -> ProcessResult:
        """Process a single music file."""

        file_hash: str | None = None
        start_time = time.perf_counter()
        current_process_id = process_id or uuid.uuid4().hex[:12]
        effective_source_root = source_root or file_path.parent
        effective_target_root = target_root or self.base_path
        warnings: list[str] = []
        lyrics_result: LyricsProcessingResult | None = None
        detected_lyrics, detection_warnings = self._find_associated_lyrics(file_path)
        associated_lyrics: Path | None = detected_lyrics
        if detection_warnings:
            warnings.extend(detection_warnings)

        try:
            # Calculate file hash.
            file_hash = self._calculate_file_hash(file_path)
            self._log_processing(
                logging.DEBUG,
                ProcessingEvent.FILE_START,
                "Processing file [id=%s, name=%s, hash=%s, dry_run=%s]",
                current_process_id,
                file_path.name,
                file_hash,
                self.dry_run,
                process_id=current_process_id,
                sequence=sequence,
                total_files=total,
                source_path=file_path,
                source_base_path=effective_source_root,
                file_hash=file_hash,
                dry_run=self.dry_run,
            )

            if self.before_dao.check_file_exists(file_hash):
                target_raw = self.before_dao.get_target_path(file_hash)
                target_path = Path(target_raw) if target_raw else None
                if target_path and target_path.exists():
                    if associated_lyrics is not None:
                        lyrics_result = self._process_associated_lyrics(
                            associated_lyrics,
                            target_path,
                            process_id=current_process_id,
                            sequence=sequence,
                            total=total,
                            source_root=effective_source_root,
                            target_root=effective_target_root,
                        )
                        warnings.extend(self._summarize_lyrics_result(lyrics_result))
                    self._log_processing(
                        logging.INFO,
                        ProcessingEvent.FILE_SKIP_DUPLICATE,
                        "File already processed [id=%s, name=%s, target=%s]",
                        current_process_id,
                        file_path.name,
                        target_path,
                        process_id=current_process_id,
                        sequence=sequence,
                        total_files=total,
                        source_path=file_path,
                        source_base_path=effective_source_root,
                        target_path=target_path,
                        target_base_path=effective_target_root,
                        file_hash=file_hash,
                    )
                    return ProcessResult(
                        source_path=file_path,
                        target_path=target_path,
                        success=True,
                        dry_run=self.dry_run,
                        file_hash=file_hash,
                        lyrics_result=lyrics_result,
                        warnings=warnings,
                    )

            # Extract metadata.
            metadata = MetadataExtractor.extract(file_path)
            if not metadata:
                raise ValueError("Failed to extract metadata")

            if metadata.artist:
                metadata.artist = self._await_romanization(metadata.artist)
            if metadata.album_artist:
                metadata.album_artist = self._await_romanization(metadata.album_artist)

            # Generate target path.
            target_path = self._generate_target_path(metadata)
            if not target_path:
                raise ValueError("Failed to generate target path")

            # Save file state.
            if not self.before_dao.insert_file(file_hash, file_path):
                raise ValueError("Failed to save file state to database")

            # If not in dry run mode, move the file and record updated state.
            if not self.dry_run:
                self._move_file(
                    file_path,
                    target_path,
                    process_id=current_process_id,
                    sequence=sequence,
                    total=total,
                    source_root=effective_source_root,
                    target_root=effective_target_root,
                )
                if not self.after_dao.insert_file(file_hash, file_path, target_path):
                    raise ValueError("Failed to save file state to database")

            if associated_lyrics is not None:
                lyrics_result = self._process_associated_lyrics(
                    associated_lyrics,
                    target_path,
                    process_id=current_process_id,
                    sequence=sequence,
                    total=total,
                    source_root=effective_source_root,
                    target_root=effective_target_root,
                )
                warnings.extend(self._summarize_lyrics_result(lyrics_result))

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_processing(
                logging.INFO,
                ProcessingEvent.FILE_SUCCESS,
                "File processed [id=%s, name=%s, target=%s, duration_ms=%.2f]",
                current_process_id,
                file_path.name,
                target_path,
                duration_ms,
                process_id=current_process_id,
                sequence=sequence,
                total_files=total,
                source_path=file_path,
                source_base_path=effective_source_root,
                target_path=target_path,
                target_base_path=effective_target_root,
                file_hash=file_hash,
                duration_ms=duration_ms,
                artist=metadata.artist,
                album=metadata.album,
                title=metadata.title,
                dry_run=self.dry_run,
            )

            return ProcessResult(
                source_path=file_path,
                target_path=target_path,
                success=True,
                dry_run=self.dry_run,
                file_hash=file_hash,
                metadata=metadata,
                lyrics_result=lyrics_result,
                warnings=warnings,
            )

        except Exception as exc:
            error_message = str(exc) if str(exc) else type(exc).__name__
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_processing(
                logging.ERROR,
                ProcessingEvent.FILE_ERROR,
                "Error processing file [id=%s, name=%s, error=%s, duration_ms=%.2f]",
                current_process_id,
                file_path.name,
                error_message,
                duration_ms,
                process_id=current_process_id,
                sequence=sequence,
                total_files=total,
                source_path=file_path,
                source_base_path=effective_source_root,
                file_hash=file_hash,
                error_message=error_message,
                duration_ms=duration_ms,
                dry_run=self.dry_run,
            )
            return ProcessResult(
                source_path=file_path,
                success=False,
                error_message=error_message,
                dry_run=self.dry_run,
                file_hash=file_hash,
                warnings=warnings,
            )

    def _is_supported(self, file: Path) -> bool:
        """Check if the given file has a supported extension.

        Args:
            file: File path to check.

        Returns:
            True if file is supported; otherwise, False.
        """
        return file.is_file() and file.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _find_associated_lyrics(self, file_path: Path) -> tuple[Path | None, list[str]]:
        """Locate an .lrc file that shares the same stem as the given music file."""

        parent = file_path.parent
        warnings: list[str] = []

        if not parent.exists():
            return None, warnings

        try:
            candidates = [
                candidate
                for candidate in parent.iterdir()
                if candidate.is_file()
                and candidate.stem == file_path.stem
                and candidate.suffix.lower() == ".lrc"
            ]
        except OSError:
            return None, warnings

        if not candidates:
            return None, warnings

        candidates.sort()
        if len(candidates) > 1:
            warnings.append(
                f"Multiple lyrics files found for {file_path.name}; using {candidates[0].name}"
            )

        return candidates[0], warnings

    def _process_associated_lyrics(
        self,
        lyrics_path: Path,
        target_file_path: Path,
        *,
        process_id: str,
        sequence: int | None,
        total: int | None,
        source_root: Path,
        target_root: Path,
    ) -> LyricsProcessingResult:
        """Move a lyrics file so that it matches the target music file path."""

        target_lyrics_path = target_file_path.with_suffix(".lrc")

        if not lyrics_path.exists():
            self._log_processing(
                logging.WARNING,
                ProcessingEvent.LYRICS_ERROR,
                "Lyrics file missing before move [id=%s, src=%s]",
                process_id,
                lyrics_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=lyrics_path,
                source_base_path=source_root,
                target_path=target_lyrics_path,
                target_base_path=target_root,
                error_message="lyrics_source_missing",
            )
            return LyricsProcessingResult(
                source_path=lyrics_path,
                target_path=target_lyrics_path,
                moved=False,
                dry_run=self.dry_run,
                reason="lyrics_source_missing",
            )

        if target_lyrics_path.exists():
            self._log_processing(
                logging.WARNING,
                ProcessingEvent.LYRICS_SKIP_CONFLICT,
                "Target lyrics already exists [id=%s, src=%s, dest=%s]",
                process_id,
                lyrics_path,
                target_lyrics_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=lyrics_path,
                source_base_path=source_root,
                target_path=target_lyrics_path,
                target_base_path=target_root,
            )
            return LyricsProcessingResult(
                source_path=lyrics_path,
                target_path=target_lyrics_path,
                moved=False,
                dry_run=self.dry_run,
                reason="target_exists",
            )

        if self.dry_run:
            self._log_processing(
                logging.INFO,
                ProcessingEvent.LYRICS_PLAN,
                "Planned lyrics move [id=%s, src=%s, dest=%s]",
                process_id,
                lyrics_path,
                target_lyrics_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=lyrics_path,
                source_base_path=source_root,
                target_path=target_lyrics_path,
                target_base_path=target_root,
                dry_run=self.dry_run,
            )
            return LyricsProcessingResult(
                source_path=lyrics_path,
                target_path=target_lyrics_path,
                moved=False,
                dry_run=True,
            )

        try:
            target_lyrics_path.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.move(str(lyrics_path), str(target_lyrics_path))
        except Exception as exc:  # pragma: no cover - defensive logging of unexpected failure
            error_message = str(exc) if str(exc) else type(exc).__name__
            self._log_processing(
                logging.ERROR,
                ProcessingEvent.LYRICS_ERROR,
                "Error moving lyrics file [id=%s, src=%s, dest=%s, error=%s]",
                process_id,
                lyrics_path,
                target_lyrics_path,
                error_message,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=lyrics_path,
                source_base_path=source_root,
                target_path=target_lyrics_path,
                target_base_path=target_root,
                error_message=error_message,
            )
            return LyricsProcessingResult(
                source_path=lyrics_path,
                target_path=target_lyrics_path,
                moved=False,
                dry_run=False,
                reason=error_message,
            )

        self._log_processing(
            logging.INFO,
            ProcessingEvent.LYRICS_MOVE,
            "Lyrics file moved [id=%s, src=%s, dest=%s]",
            process_id,
            lyrics_path,
            target_lyrics_path,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=lyrics_path,
            source_base_path=source_root,
            target_path=target_lyrics_path,
            target_base_path=target_root,
        )
        return LyricsProcessingResult(
            source_path=lyrics_path,
            target_path=target_lyrics_path,
            moved=True,
            dry_run=False,
        )

    def _summarize_lyrics_result(
        self, result: LyricsProcessingResult | None
    ) -> list[str]:
        """Convert a lyrics move outcome into user-facing warnings."""

        if result is None:
            return []

        if result.dry_run and not result.moved:
            return [
                (
                    "Dry run: lyrics "
                    f"{result.source_path.name} would move to {result.target_path.name}"
                )
            ]

        if not result.moved:
            reason_map = {
                "target_exists": "target already exists",
                "lyrics_source_missing": "source lyrics missing",
            }
            reason = result.reason or "unknown reason"
            friendly_reason = reason_map.get(reason, reason)
            return [
                f"Lyrics file {result.source_path.name} not moved: {friendly_reason}"
            ]

        return []

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
        """Move a file from the source path to the target path.

        Args:
            src_path: Original file location.
            dest_path: Destination path for the moved file.
            process_id: Optional identifier used to correlate log entries.
            sequence: Optional sequence number for the file inside a batch.
            total: Optional total number of files in the batch.
            source_root: Optional root directory used to abbreviate source paths in logs.
            target_root: Optional root directory used to abbreviate target paths in logs.
        """

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_processing(
            logging.INFO,
            ProcessingEvent.FILE_MOVE,
            "Moving file [id=%s, src=%s, dest=%s]",
            process_id or "-",
            src_path,
            dest_path,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=src_path,
            source_base_path=source_root or src_path.parent,
            target_path=dest_path,
            target_base_path=target_root or dest_path.parent,
        )
        _ = shutil.move(str(src_path), str(dest_path))

    def _cleanup_empty_directories(self, directory: Path) -> None:
        """Clean up empty directories.

        Args:
            directory: Directory to clean up.
        """
        for root, _, _ in os.walk(str(directory), topdown=False):
            try:
                root_path = Path(root)
                if root_path.exists() and not any(root_path.iterdir()):
                    root_path.rmdir()
            except OSError:
                continue

    def _generate_target_path(self, metadata: TrackMetadata) -> Path | None:
        """Generate target path for a file based on its metadata.

        Args:
            metadata: Track metadata.

        Returns:
            Target path if successful, None otherwise.
        """
        try:
            # Generate components for target directory and file name.
            dir_path = self.directory_generator.generate(metadata)
            file_name = self.file_name_generator.generate(metadata)
            if not dir_path or not file_name:
                return None

            target_path = self._find_available_path(self.base_path / dir_path / file_name)
            return target_path

        except Exception as e:
            logger.error("Error generating target path: %s", e)
            return None

    def _schedule_romanization(self, name: str) -> None:
        trimmed = name.strip()
        if not trimmed:
            return

        if trimmed in self._romanize_futures:
            return

        cached_value: str | None = None
        try:
            cached_value = self.artist_dao.get_romanized_name(trimmed)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to read cached romanized name for '%s': %s", trimmed, exc)

        if cached_value:
            logger.debug("Using persisted romanization cache for '%s'", trimmed)
            future: Future[str] = Future()
            future.set_result(cached_value)
            self._romanize_futures[trimmed] = future
            return

        def _romanize() -> str:
            return self._romanizer.romanize_name(trimmed) or trimmed

        logger.debug("Scheduling romanization task for '%s'", trimmed)
        self._romanize_futures[trimmed] = self._romanizer_executor.submit(_romanize)

    def _await_romanization(self, name: str) -> str:
        trimmed = name.strip()
        if not trimmed:
            return name
        future = self._romanize_futures.get(trimmed)
        if future is None:
            self._schedule_romanization(trimmed)
            future = self._romanize_futures.get(trimmed)
        if future is None:
            return name
        try:
            romanized = future.result()
            if romanized != trimmed:
                _ = self.artist_dao.upsert_romanized_name(trimmed, romanized)
            return romanized
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Romanization future failed for '%s': %s", trimmed, exc)
            return name

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file.

        Returns:
            Hexadecimal hash string.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _find_available_path(self, target_path: Path) -> Path:
        """Find an available file path by appending a number if needed.

        Args:
            target_path: Initial target path.

        Returns:
            Available file path.
        """
        if not target_path.exists():
            return target_path

        base = target_path.parent / target_path.stem
        extension = target_path.suffix
        counter = 1

        while True:
            new_path = Path(f"{base} ({counter}){extension}")
            if not new_path.exists():
                return new_path
            counter += 1
