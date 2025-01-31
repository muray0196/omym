"""Command executor base class."""

from abc import ABC, abstractmethod
from typing import List

from omym.core.metadata.music_file_processor import MusicProcessor, ProcessResult
from omym.ui.cli.args.options import Args
from omym.ui.cli.display.preview import PreviewDisplay
from omym.ui.cli.display.progress import ProgressDisplay
from omym.ui.cli.display.result import ResultDisplay


class CommandExecutor(ABC):
    """Base class for command execution."""

    def __init__(self, args: Args) -> None:
        """Initialize command executor.

        Args:
            args: Command line arguments.
        """
        self.args = args
        self.processor = MusicProcessor(
            base_path=args.target_path,
            dry_run=args.dry_run,
        )
        self.preview_display = PreviewDisplay()
        self.progress_display = ProgressDisplay()
        self.result_display = ResultDisplay()

    @abstractmethod
    def execute(self) -> List[ProcessResult]:
        """Execute the command.

        Returns:
            List of processing results.
        """
        pass

    def display_results(self, results: List[ProcessResult]) -> None:
        """Display command execution results.

        Args:
            results: List of processing results.
        """
        if self.args.dry_run:
            self.preview_display.show_preview(results, self.processor.base_path, show_db=self.args.show_db)
        else:
            self.result_display.show_results(results, quiet=self.args.quiet)
