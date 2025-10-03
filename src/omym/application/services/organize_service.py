"""Application service for organizing music files.

This layer centralizes orchestration and construction of domain/infra objects
so that multiple UIs (CLI, GUI) can reuse the same use cases.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, final

from omym.features.metadata import MusicProcessor, ProcessResult
from omym.features.metadata.adapters import LocalFilesystemAdapter
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

    def build_processor(self, request: OrganizeRequest) -> MusicProcessor:
        """Build and configure a ``MusicProcessor`` according to the request.

        Args:
            request: Organize operation parameters.

        Returns:
            Configured ``MusicProcessor`` instance.
        """
        processor = MusicProcessor(
            base_path=request.base_path,
            dry_run=request.dry_run,
            filesystem=LocalFilesystemAdapter(),
        )

        # Optionally clear artist cache; continue on recognized transient errors.
        if request.clear_artist_cache and hasattr(processor, "artist_dao"):
            artist_dao = getattr(processor, "artist_dao")
            if artist_dao is not None:
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
            db_manager = getattr(processor, "db_manager", None)
            conn: sqlite3.Connection | None = None
            try:
                conn = db_manager.conn if db_manager is not None else None
                if conn is not None:
                    _ = MaintenanceDAO(conn).clear_all()
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
