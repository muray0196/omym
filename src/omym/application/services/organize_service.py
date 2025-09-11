"""Application service for organizing music files.

This layer centralizes orchestration and construction of domain/infra objects
so that multiple UIs (CLI, GUI) can reuse the same use cases.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import final, Callable

from omym.domain.metadata.music_file_processor import MusicProcessor, ProcessResult


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
        processor = MusicProcessor(base_path=request.base_path, dry_run=request.dry_run)

        # Optionally clear artist cache
        if request.clear_artist_cache and hasattr(processor, "artist_dao"):
            try:
                _ = processor.artist_dao.clear_cache()
            except Exception:
                # Best-effort: cache clearing failures must not block processing
                pass

        # Optionally clear all caches and processing state
        if request.clear_cache:
            try:
                db_manager = getattr(processor, "db_manager", None)
                conn = db_manager.conn if db_manager is not None else None
                if conn is not None:
                    cur = conn.cursor()
                    # Delete in FK-safe order
                    cur.execute("DELETE FROM processing_after")
                    cur.execute("DELETE FROM track_positions")
                    cur.execute("DELETE FROM filter_values")
                    cur.execute("DELETE FROM processing_before")
                    cur.execute("DELETE FROM albums")
                    cur.execute("DELETE FROM artist_cache")
                    conn.commit()
            except Exception:
                # Best-effort clean; non-fatal if unsupported
                pass

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
        return processor.process_file(file_path)

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
