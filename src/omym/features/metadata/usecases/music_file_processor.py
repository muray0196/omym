"""Summary: High-level coordinator for organising music files into the library.
Why: Tie together romanization, persistence, and filesystem orchestration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TYPE_CHECKING

from concurrent.futures import Future

from omym.config.artist_name_preferences import (
    ArtistNamePreferenceError,
    ArtistNamePreferenceRepository,
    load_artist_name_preferences,
)
from omym.config.settings import UNPROCESSED_DIR_NAME
from omym.platform.logging import logger

from omym.shared.track_metadata import TrackMetadata
from .ports import (
    ArtistIdGeneratorPort,
    ArtistCachePort,
    DatabaseManagerPort,
    DirectoryNamingPort,
    FilesystemPort,
    FileNameGenerationPort,
    RomanizationPort,
    PreviewCachePort,
    ProcessingAfterPort,
    ProcessingBeforePort,
    RenamerPorts,
)
from .processing import (
    ProcessingEvent,
    calculate_file_hash,
    calculate_pending_unprocessed,
    generate_target_path,
    move_file,
    relocate_unprocessed_files,
    run_directory_processing,
    run_file_processing,
    snapshot_unprocessed_candidates,
)
from .extraction.romanization import RomanizationCoordinator

if TYPE_CHECKING:
    from .processing import ProcessResult

class MusicProcessor:
    """Process music files for organization."""

    SUPPORTED_EXTENSIONS: set[str] = {
        ".mp3",
        ".flac",
        ".m4a",
        ".dsf",
        ".aac",
        ".alac",
        ".opus",
    }
    SUPPORTED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".png"}

    base_path: Path
    dry_run: bool
    db_manager: DatabaseManagerPort
    before_dao: ProcessingBeforePort
    after_dao: ProcessingAfterPort
    artist_dao: ArtistCachePort
    preview_dao: PreviewCachePort
    artist_name_preferences: ArtistNamePreferenceRepository
    artist_id_generator: ArtistIdGeneratorPort
    directory_generator: DirectoryNamingPort
    file_name_generator: FileNameGenerationPort

    def __init__(
        self,
        base_path: Path,
        *,
        dry_run: bool = False,
        db_manager: DatabaseManagerPort,
        before_gateway: ProcessingBeforePort,
        after_gateway: ProcessingAfterPort,
        artist_cache: ArtistCachePort,
        romanization_port: RomanizationPort,
        preview_cache: PreviewCachePort,
        filesystem: FilesystemPort,
        renamer_ports: RenamerPorts,
    ) -> None:
        self.base_path = base_path
        self.dry_run = dry_run

        self.filesystem: FilesystemPort = filesystem
        self._romanization_port: RomanizationPort = romanization_port

        try:
            self.artist_name_preferences = load_artist_name_preferences()
        except ArtistNamePreferenceError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Failed to load artist name preference configuration: {exc}"
            ) from exc

        self.db_manager = db_manager
        if self.db_manager.conn is None:
            raise RuntimeError("Database manager must provide an active connection")

        self.before_dao = before_gateway
        self.after_dao = after_gateway
        self.preview_dao = preview_cache

        self.artist_dao = artist_cache
        self._romanization_port.configure_cache(self.artist_dao)

        self.artist_id_generator = renamer_ports.artist_id
        self.directory_generator = renamer_ports.directory
        self.file_name_generator = renamer_ports.file_name

        self._romanization: RomanizationCoordinator = RomanizationCoordinator(
            preferences=self.artist_name_preferences,
            artist_cache=self.artist_dao,
            romanization_port=self._romanization_port,
        )

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Expose hash calculation for tests and collaborators."""

        return calculate_file_hash(file_path)

    def calculate_file_hash(self, file_path: Path) -> str:
        """Public API for helper modules relying on hash calculation."""

        return self._calculate_file_hash(file_path)

    def _generate_target_path(
        self, metadata: TrackMetadata, *, existing_path: Path | None = None
    ) -> Path | None:
        """Expose target-path generation for collision staging in tests."""

        return generate_target_path(
            self.base_path,
            directory_generator=self.directory_generator,
            file_name_generator=self.file_name_generator,
            metadata=metadata,
            existing_path=existing_path,
        )

    def generate_target_path(
        self, metadata: TrackMetadata, *, existing_path: Path | None = None
    ) -> Path | None:
        """Public API consumed by helper modules."""

        return self._generate_target_path(metadata, existing_path=existing_path)

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
        """Wrapper so tests can intercept move operations via the processor."""

        move_file(
            src_path,
            dest_path,
            log=self._log_processing,
            filesystem=self.filesystem,
            process_id=process_id,
            sequence=sequence,
            total=total,
            source_root=source_root,
            target_root=target_root,
        )

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
        """Public wrapper used by helper modules."""

        self._move_file(
            src_path,
            dest_path,
            process_id=process_id,
            sequence=sequence,
            total=total,
            source_root=source_root,
            target_root=target_root,
        )

    @property
    def _romanizer_executor(self) -> ThreadPoolExecutor:
        """Provide executor access for deterministic test cleanup."""

        return self._romanization.executor

    def _schedule_romanization(self, name: str) -> None:
        """Compatibility wrapper delegating to the coordinator scheduler."""

        self._romanization.ensure_scheduled(name)

    def _await_romanization(self, name: str) -> str:
        """Compatibility wrapper delegating to the coordinator future awaiter."""

        return self._romanization.await_result(name)

    @property
    def _romanize_futures(self) -> Mapping[str, Future[str]]:
        """Expose romanization futures for legacy tests."""

        return self._romanization.futures

    @property
    def romanization(self) -> RomanizationCoordinator:
        """Expose romanization coordinator for helper modules."""

        return self._romanization

    def log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: Any,
    ) -> None:
        """Public forwarding API used by helper modules."""

        self._log_processing(level, event, message, *message_args, **context)

    def _log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: Any,
    ) -> None:
        extra: dict[str, Any] = {"processing_event": event.value}
        for key, value in context.items():
            extra[key] = str(value) if isinstance(value, Path) else value
        logger.log(level, message, *message_args, extra=extra, stacklevel=2)

    def process_directory(
        self,
        directory: Path,
        progress_callback: Callable[[int, int, Path], None] | None = None,
    ) -> list[ProcessResult]:
        return self._process_directory(directory, progress_callback)

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
        return run_file_processing(
            self,
            file_path,
            process_id=process_id,
            sequence=sequence,
            total=total,
            source_root=source_root,
            target_root=target_root,
            precomputed_metadata=precomputed_metadata,
        )

    def _process_directory(
        self,
        directory: Path,
        progress_callback: Callable[[int, int, Path], None] | None = None,
    ) -> list[ProcessResult]:
        snapshot = snapshot_unprocessed_candidates(
            directory,
            unprocessed_dir_name=UNPROCESSED_DIR_NAME,
        )
        results = run_directory_processing(
            self,
            directory,
            progress_callback,
        )

        remaining_candidates = calculate_pending_unprocessed(snapshot, results)

        _ = relocate_unprocessed_files(
            directory,
            remaining_candidates,
            unprocessed_dir_name=UNPROCESSED_DIR_NAME,
            dry_run=self.dry_run,
            filesystem=self.filesystem,
        )

        return results


__all__ = ["MusicProcessor"]
