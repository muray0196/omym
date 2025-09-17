"""Command executor base class."""

from abc import ABC, abstractmethod

from omym.domain.metadata.music_file_processor import MusicProcessor, ProcessResult
from omym.application.services.organize_service import OrganizeMusicService, OrganizeRequest
from omym.ui.cli.args.options import OrganizeArgs
from omym.ui.cli.display.preview import PreviewDisplay
from omym.ui.cli.display.progress import ProgressDisplay
from omym.ui.cli.display.result import ResultDisplay


class CommandExecutor(ABC):
    """Base class for command execution."""

    args: OrganizeArgs
    processor: MusicProcessor
    app: OrganizeMusicService
    request: OrganizeRequest
    preview_display: PreviewDisplay
    progress_display: ProgressDisplay
    result_display: ResultDisplay

    def __init__(self, args: OrganizeArgs) -> None:
        """Initialize command executor.

        Args:
            args: Command line arguments.
        """
        self.args = args
        # Build processor through application layer to centralize orchestration
        self.app = OrganizeMusicService()
        self.request = OrganizeRequest(
            base_path=args.target_path,
            dry_run=args.dry_run,
            clear_artist_cache=args.clear_artist_cache,
            clear_cache=getattr(args, "clear_cache", False),
        )
        self.processor = self.app.build_processor(self.request)
        self.preview_display = PreviewDisplay()
        self.progress_display = ProgressDisplay()
        self.result_display = ResultDisplay()
        # Logging of cache clears is handled at service-level as best-effort; keep CLI silent here

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
