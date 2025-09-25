"""Progress display functionality for CLI."""

from pathlib import Path
from typing import Any, Callable, Protocol, final, runtime_checkable
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.prompt import Prompt

from omym.application.services.organize_service import OrganizeRequest
from omym.features.metadata import ProcessResult
from omym.platform.logging import WhitePathRichHandler, logger

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

        progress_console: Console | None = None
        for handler in logger.handlers:
            if isinstance(handler, WhitePathRichHandler):
                progress_console = handler.console
                break

        progress_kwargs: dict[str, Any] = {
            "transient": True,
            "redirect_stdout": False,
            "redirect_stderr": False,
        }
        if progress_console is not None:
            progress_kwargs["console"] = progress_console

        with Progress(**progress_kwargs) as progress:
            task_id: TaskID | None = None
            last_count = 0

            def _cb(processed: int, total: int, current_file: Path) -> None:
                nonlocal task_id, last_count
                _ = current_file  # consumed via logging elsewhere
                if task_id is None:
                    task_id = progress.add_task("[cyan]Processing files...", total=total)
                advance = processed - last_count
                if advance < 0:
                    advance = 0
                _ = progress.update(
                    task_id,
                    advance=advance,
                    description=f"[cyan]Processing files... {processed}/{total}",
                )
                last_count = processed

            results = app.process_directory_with_progress(request, directory, _cb)

        if interactive:
            failed_results = [result for result in results if not result.success]
            if failed_results:
                console = progress_console or Console()

                def _render_failure(detail_result: ProcessResult) -> None:
                    console.print(f"[red]- {detail_result.source_path}[/red]")
                    if detail_result.error_message:
                        console.print(f"[red]  Error: {detail_result.error_message}[/red]")
                    else:
                        console.print("[red]  Error: <no message provided>[/red]")
                    if detail_result.target_path is not None:
                        console.print(f"[cyan]  Target: {detail_result.target_path}[/cyan]")
                    if detail_result.dry_run:
                        console.print("[yellow]  Note: Result produced in dry-run mode.[/yellow]")

                option_map: dict[str, ProcessResult] = {
                    str(index + 1): result for index, result in enumerate(failed_results)
                }
                console.print(
                    f"\n[bold red]Processing completed with {len(failed_results)} failure(s).[/bold red]"
                )
                console.print("[bold]Failed items:[/bold]")
                for key, result in option_map.items():
                    console.print(f"  [{key}] {result.source_path}")
                console.print(
                    "Enter the number of a failed item to inspect, 'a' to show all, or 'q' to continue."
                )

                choices = list(option_map.keys()) + ["a", "q"]
                prompt_message = "Selection"

                while True:
                    try:
                        selection = Prompt.ask(
                            prompt_message,
                            choices=choices,
                            default="q",
                            show_choices=False,
                        )
                    except (EOFError, KeyboardInterrupt):
                        console.print("[yellow]Interactive session cancelled by user.")
                        break

                    if selection == "q":
                        break
                    if selection == "a":
                        for failed_result in failed_results:
                            _render_failure(failed_result)
                        continue

                    failed_result = option_map[selection]
                    _render_failure(failed_result)

        return results
