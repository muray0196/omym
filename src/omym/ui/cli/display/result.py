"""src/omym/ui/cli/display/result.py
What: Render user-facing summaries for organise/restore CLI flows.
Why: Keep console output formatting consistent across the interface.
"""

from __future__ import annotations

from typing import final

from rich.console import Console

from omym.features.metadata import ProcessResult
from omym.ui.cli.models import UnprocessedSummary

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

    def show_unprocessed_summary(self, summary: UnprocessedSummary, *, quiet: bool = False) -> None:
        """Render the pending-unprocessed report including optional previews."""

        if quiet:
            return

        total = summary.total
        self.console.print(f"Unprocessed files awaiting review: {total}")

        if total == 0:
            return

        for candidate in summary.preview:
            self.console.print(f"  • {candidate}")

        if summary.truncated:
            remaining = total - len(summary.preview)
            if remaining > 0:
                self.console.print(f"...and {remaining} more.")
