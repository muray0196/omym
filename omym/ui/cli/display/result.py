"""Result display functionality for CLI."""

from typing import final
from rich.console import Console

from omym.core.metadata.music_file_processor import ProcessResult


@final
class ResultDisplay:
    """Handles result display in CLI."""

    console: Console

    def __init__(self) -> None:
        """Initialize result display."""
        self.console = Console()

    def show_results(self, results: list[ProcessResult], quiet: bool = False) -> None:
        """Display processing results.

        Args:
            results: List of processing results.
            quiet: Whether to suppress non-error output.
        """
        if quiet:
            return

        self.console.print("\n[bold]Processing Summary:[/bold]")
        self.console.print(f"Total files processed: {len(results)}")
        self.console.print(f"[green]Successful: {sum(1 for r in results if r.success)}[/green]")
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            self.console.print(f"[red]Failed: {failed_count}[/red]")
            for result in results:
                if not result.success:
                    self.console.print(f"[red]  • {result.source_path}: {result.error_message}[/red]")
