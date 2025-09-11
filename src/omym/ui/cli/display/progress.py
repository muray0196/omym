"""Progress display functionality for CLI."""

from pathlib import Path
from typing import final, Protocol, Callable, runtime_checkable
from rich.progress import Progress, TaskID

from omym.application.services.organize_service import OrganizeRequest
from omym.domain.metadata.music_file_processor import ProcessResult


@runtime_checkable
class OrganizeServiceLike(Protocol):
    """Protocol for application services that can process a directory with progress."""

    def process_directory_with_progress(
        self,
        request: OrganizeRequest,
        directory: Path,
        progress_callback: Callable[[int, int, Path], None],
    ) -> list[ProcessResult]:
        ...


@final
class ProgressDisplay:
    """Handles progress display in CLI."""

    def run_with_service(
        self,
        app: OrganizeServiceLike,
        request: OrganizeRequest,
        directory: Path,
        interactive: bool = False,
    ) -> list[ProcessResult]:
        """Run directory processing via application service with progress bar.

        Args:
            app: Application service instance used to orchestrate processing.
            request: Organize operation parameters.
            directory: Directory to process.
            interactive: Whether to run in interactive mode.

        Returns:
            List of processing results.
        """
        results: list[ProcessResult] = []

        with Progress() as progress:
            task_id: TaskID | None = None
            last_count = 0

            def _cb(processed: int, total: int, current_file: Path) -> None:
                nonlocal task_id, last_count
                if task_id is None:
                    task_id = progress.add_task("[cyan]Processing files...", total=total)
                advance = processed - last_count
                if advance < 0:
                    advance = 0
                # Update description with current file name for better UX
                _ = progress.update(task_id, advance=advance, description=f"[cyan]Processing {current_file.name}...")
                last_count = processed

            results = app.process_directory_with_progress(request, directory, _cb)

        # Placeholder for future interactive handling
        if interactive:
            # TODO: Implement interactive handling for failed items
            pass

        return results
