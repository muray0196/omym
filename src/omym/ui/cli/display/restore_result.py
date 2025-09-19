"""Display utilities for restore command results."""

from __future__ import annotations

from typing import Final, final
from rich.console import Console

from omym.domain.restoration import RestoreResult


SKIPPED_MESSAGES: Final[set[str]] = {"dry_run", "destination_exists", "already_restored"}


@final
class RestoreResultDisplay:
    """Render restoration outcomes in the CLI."""

    def __init__(self) -> None:
        self.console = Console()

    def show_results(self, results: list[RestoreResult], *, quiet: bool = False) -> None:
        """Print a summary of restoration results."""

        if quiet:
            return

        total = len(results)
        restored = sum(1 for result in results if result.moved)
        skipped = sum(
            1
            for result in results
            if not result.moved and (result.message in SKIPPED_MESSAGES)
        )
        failed = total - restored - skipped

        self.console.print("\n[bold]Restore Summary:[/bold]")
        self.console.print(f"Total candidates: {total}")
        self.console.print(f"[green]Restored: {restored}[/green]")
        if skipped:
            self.console.print(f"[yellow]Skipped: {skipped}[/yellow]")
        if failed:
            self.console.print(f"[red]Failed: {failed}[/red]")
            for result in results:
                if result.moved:
                    continue
                if result.message in SKIPPED_MESSAGES:
                    continue
                detail = result.message or "unknown error"
                self.console.print(
                    f"[red]  • {result.plan.source_path} → {result.plan.destination_path}: {detail}[/red]"
                )
