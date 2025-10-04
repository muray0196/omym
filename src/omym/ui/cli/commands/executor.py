"""src/omym/ui/cli/commands/executor.py
What: Provide shared wiring for CLI command executors.
Why: Reuse orchestration and presentation helpers across commands.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from omym.config.settings import UNPROCESSED_DIR_NAME, UNPROCESSED_PREVIEW_LIMIT
from omym.features.metadata import MusicProcessor, ProcessResult
from omym.application.services.organize_service import OrganizeMusicService, OrganizeRequest
from omym.ui.cli.args.options import OrganizeArgs
from omym.ui.cli.display.preview import PreviewDisplay
from omym.ui.cli.display.progress import ProgressDisplay
from omym.ui.cli.display.result import ResultDisplay
from omym.ui.cli.models import UnprocessedSummary
from omym.features.metadata.usecases.processing import (
    calculate_pending_unprocessed,
    snapshot_unprocessed_candidates,
)


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
    ) -> UnprocessedSummary:
        """Summarise which files still require manual review after a run."""

        pending_paths = self._collect_pending_paths(source_root, results)
        total = len(pending_paths)

        if total == 0:
            return UnprocessedSummary(total=0, preview=[], truncated=False)

        sorted_paths = sorted(
            (self._to_relative_display_path(source_root, candidate) for candidate in pending_paths),
        )

        limit = 0 if self.args.show_all_unprocessed else UNPROCESSED_PREVIEW_LIMIT
        preview = sorted_paths if limit <= 0 else sorted_paths[:limit]
        truncated = len(preview) < total

        return UnprocessedSummary(total=total, preview=preview, truncated=truncated)

    def _collect_pending_paths(
        self,
        source_root: Path,
        results: Sequence[ProcessResult],
    ) -> set[Path]:
        """Gather filesystem paths that remain unprocessed after orchestration."""

        if self.request.dry_run:
            snapshot = snapshot_unprocessed_candidates(
                source_root,
                unprocessed_dir_name=UNPROCESSED_DIR_NAME,
            )
            pending_candidates = calculate_pending_unprocessed(snapshot, results)
            return {path for path in pending_candidates if path.is_file()}

        unprocessed_root = source_root / UNPROCESSED_DIR_NAME
        if not unprocessed_root.exists():
            return set()

        return {candidate for candidate in unprocessed_root.rglob("*") if candidate.is_file()}

    @staticmethod
    def _to_relative_display_path(source_root: Path, candidate: Path) -> str:
        """Render a candidate path relative to the root when possible."""

        try:
            return str(candidate.relative_to(source_root))
        except ValueError:
            return str(candidate)
