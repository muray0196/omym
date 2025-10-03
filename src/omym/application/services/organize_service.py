"""Application service for organizing music files.

This layer centralizes orchestration and construction of domain/infra objects
so that multiple UIs (CLI, GUI) can reuse the same use cases.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, final

from omym.features.metadata import MusicProcessor, ProcessResult
from omym.features.metadata.adapters import LocalFilesystemAdapter
from omym.features.metadata.usecases.ports import (
    ArtistCachePort,
    DatabaseManagerPort,
    FilesystemPort,
    PreviewCachePort,
    ProcessingAfterPort,
    ProcessingBeforePort,
)
from omym.features.metadata.usecases.extraction.artist_cache_adapter import (
    DryRunArtistCacheAdapter,
)
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.db.daos.processing_after_dao import ProcessingAfterDAO
from omym.platform.db.daos.processing_before_dao import ProcessingBeforeDAO
from omym.platform.db.daos.processing_preview_dao import ProcessingPreviewDAO
from omym.platform.db.db_manager import DatabaseManager
from omym.platform.db.daos.maintenance_dao import MaintenanceDAO
from omym.platform.logging import logger

CACHE_CLEAR_EXCEPTIONS: tuple[type[Exception], ...] = (sqlite3.Error,)


@dataclass(frozen=True)
class OrganizeRequest:
    """Input parameters for organizing operations.

    Attributes:
        base_path: Root directory for organized output.
        dry_run: If True, performs no file mutations.
        clear_artist_cache: Clear artist cache before processing.
        clear_cache: Clear all caches and processing state before processing.
    """

    base_path: Path
    dry_run: bool = False
    clear_artist_cache: bool = False
    clear_cache: bool = False


@final
class OrganizeMusicService:
    """Application service that orchestrates organizing music files.

    This service constructs the domain processor and applies cache-clearing
    semantics in one place so UIs don't need to reach into infra details.
    """

    def __init__(
        self,
        *,
        filesystem_factory: Callable[[], FilesystemPort] | None = None,
        db_factory: Callable[[], DatabaseManagerPort] | None = None,
        before_factory: Callable[[sqlite3.Connection], ProcessingBeforePort] | None = None,
        after_factory: Callable[[sqlite3.Connection], ProcessingAfterPort] | None = None,
        preview_factory: Callable[[sqlite3.Connection], PreviewCachePort] | None = None,
        artist_factory: Callable[[sqlite3.Connection], ArtistCacheDAO] | None = None,
        dry_run_artist_factory: Callable[[ArtistCacheDAO], ArtistCachePort] | None = None,
        maintenance_factory: Callable[[sqlite3.Connection], MaintenanceDAO] | None = None,
        processor_factory: Callable[..., MusicProcessor] | None = None,
    ) -> None:
        """Create a service with overridable infrastructure factories.

        Tests can inject light-weight doubles while production code relies on
        the default adapters and DAOs.
        """

        self._filesystem_factory: Callable[[], FilesystemPort] = (
            filesystem_factory or LocalFilesystemAdapter
        )
        self._db_factory: Callable[[], DatabaseManagerPort] = (
            db_factory or DatabaseManager
        )
        self._before_factory: Callable[[sqlite3.Connection], ProcessingBeforePort] = (
            before_factory or ProcessingBeforeDAO
        )
        self._after_factory: Callable[[sqlite3.Connection], ProcessingAfterPort] = (
            after_factory or ProcessingAfterDAO
        )
        self._preview_factory: Callable[[sqlite3.Connection], PreviewCachePort] = (
            preview_factory or ProcessingPreviewDAO
        )
        self._artist_factory: Callable[[sqlite3.Connection], ArtistCacheDAO] = (
            artist_factory or ArtistCacheDAO
        )
        self._dry_run_artist_factory: Callable[[ArtistCacheDAO], ArtistCachePort] = (
            dry_run_artist_factory or DryRunArtistCacheAdapter
        )
        self._maintenance_factory: Callable[[sqlite3.Connection], MaintenanceDAO] = (
            maintenance_factory or MaintenanceDAO
        )
        self._processor_factory: Callable[..., MusicProcessor] = (
            processor_factory or MusicProcessor
        )

    def build_processor(self, request: OrganizeRequest) -> MusicProcessor:
        """Build and configure a ``MusicProcessor`` according to the request.

        Args:
            request: Organize operation parameters.

        Returns:
            Configured ``MusicProcessor`` instance.
        """
        filesystem = self._filesystem_factory()
        db_manager = self._db_factory()
        if db_manager.conn is None:
            db_manager.connect()
        conn = db_manager.conn
        if conn is None:
            raise RuntimeError("Database connection could not be established")

        before_dao = self._before_factory(conn)
        after_dao = self._after_factory(conn)
        preview_dao = self._preview_factory(conn)
        base_artist_dao = self._artist_factory(conn)
        artist_dao: ArtistCachePort
        if request.dry_run:
            artist_dao = self._dry_run_artist_factory(base_artist_dao)
        else:
            artist_dao = base_artist_dao

        processor = self._processor_factory(
            base_path=request.base_path,
            dry_run=request.dry_run,
            db_manager=db_manager,
            before_gateway=before_dao,
            after_gateway=after_dao,
            artist_cache=artist_dao,
            preview_cache=preview_dao,
            filesystem=filesystem,
        )

        # Optionally clear artist cache; continue on recognized transient errors.
        if request.clear_artist_cache:
            artist_dao = processor.artist_dao
            try:
                _ = artist_dao.clear_cache()
            except Exception as exc:
                if isinstance(exc, CACHE_CLEAR_EXCEPTIONS):
                    logger.warning(
                        (
                            "build_processor: clear_artist_cache requested but "
                            "artist_dao.clear_cache() failed; continuing without "
                            "flushing the persistent artist cache. error=%s"
                        ),
                        exc,
                    )
                else:
                    raise

        # Optionally clear all caches and processing state when requested.
        if request.clear_cache:
            db_manager = processor.db_manager
            conn = db_manager.conn
            try:
                if conn is not None:
                    maintenance = self._maintenance_factory(conn)
                    _ = maintenance.clear_all()
            except Exception as exc:
                if isinstance(exc, CACHE_CLEAR_EXCEPTIONS):
                    logger.warning(
                        (
                            "build_processor: clear_cache requested but "
                            "MaintenanceDAO.clear_all() failed for connection %r; "
                            "continuing without clearing persistent processing state. "
                            "error=%s"
                        ),
                        conn,
                        exc,
                    )
                else:
                    raise

        return processor

    def process_file(self, request: OrganizeRequest, file_path: Path) -> ProcessResult:
        """Process a single file via a freshly built processor.

        Args:
            request: Organize operation parameters.
            file_path: Path to the music file to process.

        Returns:
            Processing result object.
        """
        processor = self.build_processor(request)
        return processor.process_file(
            file_path,
            source_root=file_path.parent,
            target_root=request.base_path,
        )

    def process_directory(self, request: OrganizeRequest, directory: Path) -> list[ProcessResult]:
        """Process a directory via a freshly built processor.

        Args:
            request: Organize operation parameters.
            directory: Directory containing files to process.

        Returns:
            List of processing results.
        """
        processor = self.build_processor(request)
        return processor.process_directory(directory)

    def process_directory_with_progress(
        self,
        request: OrganizeRequest,
        directory: Path,
        progress_callback: Callable[[int, int, Path], None],
    ) -> list[ProcessResult]:
        """Process a directory and report progress through a callback.

        Args:
            request: Organize operation parameters.
            directory: Directory containing files to process.
            progress_callback: Callback that receives (processed_count, total_count, current_file_path).

        Returns:
            List of processing results.
        """
        processor = self.build_processor(request)
        return processor.process_directory(directory, progress_callback=progress_callback)
