"""Command executor base class."""

from abc import ABC, abstractmethod

from omym.domain.metadata.music_file_processor import MusicProcessor, ProcessResult
from omym.infra.logger.logger import logger
from omym.ui.cli.args.options import Args
from omym.ui.cli.display.preview import PreviewDisplay
from omym.ui.cli.display.progress import ProgressDisplay
from omym.ui.cli.display.result import ResultDisplay


class CommandExecutor(ABC):
    """Base class for command execution."""

    args: Args
    processor: MusicProcessor
    preview_display: PreviewDisplay
    progress_display: ProgressDisplay
    result_display: ResultDisplay

    def __init__(self, args: Args) -> None:
        """Initialize command executor.

        Args:
            args: Command line arguments.
        """
        self.args = args
        if args.target_path is None:
            raise ValueError("Target path is required")
        self.processor = MusicProcessor(
            base_path=args.target_path,
            dry_run=args.dry_run,
        )
        self.preview_display = PreviewDisplay()
        self.progress_display = ProgressDisplay()
        self.result_display = ResultDisplay()

        # Optionally clear artist cache before processing
        try:
            if args.clear_artist_cache:
                if hasattr(self.processor, "artist_dao") and self.processor.artist_dao.clear_cache():
                    logger.info("Artist cache cleared")
                else:
                    logger.warning("Failed to clear artist cache or DAO unavailable")
        except Exception as e:
            logger.warning("Error while clearing artist cache: %s", e)

        # Optionally clear all caches and processing state
        try:
            if getattr(args, "clear_cache", False):
                db_manager = getattr(self.processor, "db_manager", None)
                conn = db_manager.conn if db_manager is not None else None
                if conn is None:
                    logger.warning("Database connection unavailable; cannot clear cache")
                else:
                    cur = conn.cursor()
                    # Delete in FK-safe order
                    cur.execute("DELETE FROM processing_after")
                    cur.execute("DELETE FROM track_positions")
                    cur.execute("DELETE FROM filter_values")
                    cur.execute("DELETE FROM processing_before")
                    cur.execute("DELETE FROM albums")
                    cur.execute("DELETE FROM artist_cache")
                    conn.commit()
                    logger.info("All caches and processing state cleared")
        except Exception as e:
            logger.warning("Error while clearing caches: %s", e)

    @abstractmethod
    def execute(self) -> list[ProcessResult]:
        """Execute the command.

        Returns:
            List of processing results.
        """
        pass

    def display_results(self, results: list[ProcessResult]) -> None:
        """Display command execution results.

        Args:
            results: List of processing results.
        """
        if self.args.dry_run:
            self.preview_display.show_preview(results, self.processor.base_path, show_db=self.args.show_db)
        else:
            self.result_display.show_results(results, quiet=self.args.quiet)
