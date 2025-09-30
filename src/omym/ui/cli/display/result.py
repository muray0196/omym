"""src/omym/ui/cli/display/result.py
What: Render user-facing summaries for organise/restore CLI flows.
Why: Keep console output formatting consistent across the interface.
"""

from typing import final

from rich.console import Console

from omym.features.metadata import ProcessResult

from .summary import render_processing_summary

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

        render_processing_summary(
            console=self.console,
            results=results,
            header_label="Processing Summary",
            total_label="Total files processed",
            success_label="Successful",
            failure_label="Failed",
        )

    def show_unprocessed_total(self, pending_count: int, *, quiet: bool = False) -> None:
        """Render the count of files that still require manual review."""

        if quiet:
            return

        self.console.print(f"Unprocessed files awaiting review: {pending_count}")
