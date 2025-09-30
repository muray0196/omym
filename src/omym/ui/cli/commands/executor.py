"""src/omym/ui/cli/commands/executor.py
What: Provide shared wiring for CLI command executors.
Why: Reuse orchestration and presentation helpers across commands.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from omym.config.settings import UNPROCESSED_DIR_NAME
from omym.features.metadata import MusicProcessor, ProcessResult
from omym.application.services.organize_service import OrganizeMusicService, OrganizeRequest
from omym.ui.cli.args.options import OrganizeArgs
from omym.ui.cli.display.preview import PreviewDisplay
from omym.ui.cli.display.progress import ProgressDisplay
from omym.ui.cli.display.result import ResultDisplay
from omym.features.metadata.usecases.unprocessed_cleanup import snapshot_unprocessed_candidates


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

    def calculate_unprocessed_pending(
        self,
        source_root: Path,
        results: Sequence[ProcessResult],
    ) -> int:
        """Return the number of files that remain outside the organised targets."""

        if self.request.dry_run:
            pending_candidates = snapshot_unprocessed_candidates(
                source_root,
                unprocessed_dir_name=UNPROCESSED_DIR_NAME,
            )

            for result in results:
                if not result.success:
                    continue
                source_path = result.source_path
                if source_path in pending_candidates:
                    pending_candidates.discard(source_path)
                lyrics_result = result.lyrics_result
                if (
                    lyrics_result is not None
                    and lyrics_result.source_path in pending_candidates
                    and lyrics_result.reason is None
                ):
                    pending_candidates.discard(lyrics_result.source_path)
                for artwork_result in result.artwork_results:
                    if (
                        artwork_result.source_path in pending_candidates
                        and artwork_result.reason is None
                    ):
                        pending_candidates.discard(artwork_result.source_path)

            return sum(1 for path in pending_candidates if path.exists() and path.is_file())

        unprocessed_root = source_root / UNPROCESSED_DIR_NAME
        if not unprocessed_root.exists():
            return 0

        return sum(1 for candidate in unprocessed_root.rglob("*") if candidate.is_file())
