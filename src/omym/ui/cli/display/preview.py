"""src/omym/ui/cli/display/preview.py
Where: CLI adapter layer for preview rendering.
What: Build Rich trees that preview planned metadata operations.
Why: Provide users with a safe, visual diff before applying changes.
"""

from pathlib import Path
from typing import Literal, final
from rich.console import Console
from rich.tree import Tree

from omym.features.metadata import ProcessResult

from .summary import render_processing_summary

@final
class PreviewDisplay:
    """Handles preview display in CLI."""

    console: Console

    def __init__(self) -> None:
        """Initialize preview display."""
        self.console = Console()

    def show_preview(self, results: list[ProcessResult], base_path: Path, show_db: bool = False) -> None:
        """Display a preview of the planned file organization."""

        self.console.print("\n[bold cyan]Preview of planned changes:[/bold cyan]")

        tree = Tree(f"📁 {base_path}")
        current_artist: str | None = None
        current_album: str | None = None
        artist_node = None
        album_node = None

        def add_entry(
            path: Path,
            success: bool,
            dry_run: bool,
            warning_reason: str | None,
            entry_type: Literal["audio", "lyrics", "artwork"],
        ) -> None:
            nonlocal current_artist, current_album, artist_node, album_node

            try:
                rel_path = path.relative_to(base_path)
            except ValueError:
                rel_path = path

            parts = rel_path.parts
            if not parts:
                return

            if current_artist is None or parts[0] != current_artist:
                current_artist = parts[0]
                artist_node = tree.add(f"📁 {current_artist}")
                current_album = None

            if len(parts) >= 2 and (current_album is None or parts[1] != current_album):
                current_album = parts[1]
                if artist_node is not None:
                    album_node = artist_node.add(f"📁 {current_album}")

            target_node = album_node or artist_node or tree
            icon, status = self._determine_preview_icon(
                entry_type,
                success,
                dry_run,
                warning_reason,
            )
            type_marker = {
                "audio": "🎵",
                "lyrics": "📝",
                "artwork": "🖼️",
            }[entry_type]
            filename = rel_path.name
            label = f"{type_marker} {icon} {filename} {status}"
            _ = target_node.add(label)

        sorted_results = sorted(
            [result for result in results if result.target_path],
            key=lambda result: str(result.target_path),
        )

        for result in sorted_results:
            if not result.target_path:
                continue

            add_entry(result.target_path, result.success, result.dry_run, None, "audio")

            lyrics_result = result.lyrics_result
            if lyrics_result and lyrics_result.target_path:
                warning_reason: str | None = None
                if not lyrics_result.moved and not lyrics_result.dry_run:
                    warning_reason = self._format_lyrics_warning(lyrics_result.reason)
                add_entry(
                    lyrics_result.target_path,
                    lyrics_result.moved or lyrics_result.dry_run,
                    lyrics_result.dry_run,
                    warning_reason,
                    "lyrics",
                )

            for artwork_result in result.artwork_results:
                if not artwork_result.target_path:
                    continue

                artwork_warning: str | None = None
                if not artwork_result.moved and not artwork_result.dry_run:
                    artwork_warning = self._format_artwork_warning(artwork_result.reason)

                add_entry(
                    artwork_result.target_path,
                    artwork_result.moved or artwork_result.dry_run,
                    artwork_result.dry_run,
                    artwork_warning,
                    "artwork",
                )

        self.console.print(tree)

        if show_db:
            self._show_db_preview(results)

        self._show_summary(results)

    def _determine_preview_icon(
        self,
        entry_type: Literal["audio", "lyrics", "artwork"],
        success: bool,
        dry_run: bool,
        warning_reason: str | None,
    ) -> tuple[str, str]:
        """Return the icon and status label for a preview entry."""

        if warning_reason:
            warning_prefix = {
                "audio": "Skipped",
                "lyrics": "Skipped",
                "artwork": "Skipped",
            }[entry_type]
            return "\u26a0\ufe0f", f"[yellow]{warning_prefix} ({warning_reason})[/yellow]"
        if not success:
            return "\u274c", "[red]Error[/red]"
        if dry_run:
            return "\u2728", "[yellow]Preview[/yellow]"
        return "\u2705", "[green]Done[/green]"

    def _format_lyrics_warning(self, reason: str | None) -> str:
        """Convert an internal lyrics warning reason into a user-facing message."""

        if reason is None:
            return "skipped"

        normalized = reason.strip()
        if not normalized:
            return "skipped"

        mapping = {
            "target_exists": "target already exists",
            "lyrics_source_missing": "source lyrics missing",
        }
        return mapping.get(normalized, normalized.replace("_", " "))

    def _format_artwork_warning(self, reason: str | None) -> str:
        """Convert an artwork warning reason into a user-facing message."""

        if reason is None:
            return "skipped"

        normalized = reason.strip()
        if not normalized:
            return "skipped"

        mapping = {
            "target_exists": "target already exists",
            "source_missing": "source artwork missing",
            "already_at_target": "already at destination",
            "no_target_track": "target track unavailable",
        }
        return mapping.get(normalized, normalized.replace("_", " "))

    def _show_db_preview(self, results: list[ProcessResult]) -> None:
        """Display a preview of database operations.

        Args:
            results: List of processing results.
        """
        from rich.table import Table

        self.console.print("\n[bold magenta]Database Operations Preview:[/bold magenta]")

        # Create tables for each database operation type
        artist_table = Table(title="Artist Cache Updates")
        _ = artist_table.add_column("Artist Name", style="cyan")
        _ = artist_table.add_column("Artist ID", style="green")
        _ = artist_table.add_column("Operation", style="yellow")

        before_table = Table(title="Processing Before Records")
        _ = before_table.add_column("File Hash", style="cyan", no_wrap=True)
        _ = before_table.add_column("Source Path", style="blue")
        _ = before_table.add_column("Metadata", style="green")

        after_table = Table(title="Processing After Records")
        _ = after_table.add_column("File Hash", style="cyan", no_wrap=True)
        _ = after_table.add_column("Target Path", style="blue")
        _ = after_table.add_column("Status", style="yellow")

        # Collect unique artists and their IDs
        artists_seen: dict[str, str] = {}  # artist_name -> artist_id
        for result in results:
            if result.metadata and result.metadata.artist:
                artist = result.metadata.artist
                # Extract artist ID from the target file name
                if result.target_path:
                    file_name = result.target_path.name
                    # Artist ID is the last part before the extension
                    artist_id = file_name.rsplit("_", 1)[-1].split(".")[0]
                    if 1 <= len(artist_id) <= 5:  # Valid artist ID length (up to 5)
                        artists_seen[artist] = artist_id

        # Add rows to artist table
        for artist, artist_id in sorted(artists_seen.items()):
            _ = artist_table.add_row(
                artist,
                artist_id,
                "Cache Update",
            )

        # Add processing records
        for result in results:
            if result.file_hash:
                # Before record
                _ = before_table.add_row(
                    result.file_hash,
                    str(result.source_path),
                    str(result.metadata) if result.metadata else "N/A",
                )

                # After record
                _ = after_table.add_row(
                    result.file_hash,
                    str(result.target_path) if result.target_path else "N/A",
                    "Success" if result.success else f"Error: {result.error_message}",
                )

        # Print tables if they have data
        if artists_seen:
            self.console.print(artist_table)
        self.console.print(before_table)
        self.console.print(after_table)

    def _show_summary(self, results: list[ProcessResult]) -> None:
        """Display a summary of processing results.

        Args:
            results: List of processing results.
        """
        render_processing_summary(
            console=self.console,
            results=results,
            header_label="Summary",
            total_label="Total files to process",
            success_label="Will succeed",
            failure_label="Will fail",
        )
