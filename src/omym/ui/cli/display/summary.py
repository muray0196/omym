"""Utilities for rendering shared CLI display content."""

from __future__ import annotations

from collections.abc import Sequence

from rich.console import Console

from omym.features.metadata import ProcessResult


def render_processing_summary(
    console: Console,
    results: Sequence[ProcessResult],
    header_label: str,
    total_label: str,
    success_label: str,
    failure_label: str,
) -> None:
    """Render a formatted summary of processing outcomes.

    Args:
        console: Rich console instance used to render output.
        results: Sequence of processing results to summarize.
        header_label: Label rendered in the summary header.
        total_label: Label describing the total count of processed items.
        success_label: Label describing the count of successful results.
        failure_label: Label describing the count of failed results.
    """
    success_count = sum(1 for result in results if result.success)
    failure_results = [result for result in results if not result.success]
    total_count = len(results)

    console.print(f"\n[bold]{header_label}:[/bold]")
    console.print(f"{total_label}: {total_count}")
    console.print(f"[green]{success_label}: {success_count}[/green]")

    if not failure_results:
        return

    console.print(f"[red]{failure_label}: {len(failure_results)}[/red]")
    for failed_result in failure_results:
        console.print(
            f"[red]  • {failed_result.source_path}: {failed_result.error_message}[/red]"
        )
