"""Preview display functionality for CLI."""

from pathlib import Path
from typing import List
from rich.console import Console
from rich.tree import Tree

from omym.core.metadata.music_file_processor import ProcessResult


class PreviewDisplay:
    """Handles preview display in CLI."""

    def __init__(self) -> None:
        """Initialize preview display."""
        self.console = Console()

    def show_preview(self, results: List[ProcessResult], base_path: Path, show_db: bool = False) -> None:
        """Display a preview of the planned file organization.

        Args:
            results: List of processing results.
            base_path: Base path for the music library.
            show_db: Whether to show database operations preview.
        """
        self.console.print("\n[bold cyan]Preview of planned changes:[/bold cyan]")

        # Create a tree structure for visualization
        tree = Tree(f"📁 {base_path}")
        current_artist = None
        current_album = None
        artist_node = None
        album_node = None

        # Sort results by target path to group by artist/album
        sorted_results = sorted(
            [r for r in results if r.target_path],
            key=lambda r: str(r.target_path)
        )

        for result in sorted_results:
            if not result.target_path:
                continue

            # Get relative paths
            rel_path = result.target_path.relative_to(base_path)
            parts = rel_path.parts

            if len(parts) >= 1 and parts[0] != current_artist:
                current_artist = parts[0]
                artist_node = tree.add(f"📁 {current_artist}")
                current_album = None

            if len(parts) >= 2 and parts[1] != current_album:
                current_album = parts[1]
                if artist_node:
                    album_node = artist_node.add(f"📁 {current_album}")

            if album_node and len(parts) >= 3:
                icon = "❌" if not result.success else "✨" if result.dry_run else "✅"
                status = (
                    "[red]Error[/red]"
                    if not result.success
                    else "[yellow]Preview[/yellow]"
                    if result.dry_run
                    else "[green]Done[/green]"
                )
                album_node.add(f"{icon} {parts[-1]} {status}")

        # Print the tree
        self.console.print(tree)

        # Show database operations if requested
        if show_db:
            self._show_db_preview(results)

        # Print summary
        self._show_summary(results)

    def _show_db_preview(self, results: List[ProcessResult]) -> None:
        """Display a preview of database operations.

        Args:
            results: List of processing results.
        """
        from rich.table import Table

        self.console.print("\n[bold magenta]Database Operations Preview:[/bold magenta]")

        # Create tables for each database operation type
        artist_table = Table(title="Artist Cache Updates")
        artist_table.add_column("Artist Name", style="cyan")
        artist_table.add_column("Artist ID", style="green")
        artist_table.add_column("Operation", style="yellow")

        before_table = Table(title="Processing Before Records")
        before_table.add_column("File Hash", style="cyan", no_wrap=True)
        before_table.add_column("Source Path", style="blue")
        before_table.add_column("Metadata", style="green")

        after_table = Table(title="Processing After Records")
        after_table.add_column("File Hash", style="cyan", no_wrap=True)
        after_table.add_column("Target Path", style="blue")
        after_table.add_column("Status", style="yellow")

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
                    if len(artist_id) == 5:  # Valid artist ID length
                        artists_seen[artist] = artist_id

        # Add rows to artist table
        for artist, artist_id in sorted(artists_seen.items()):
            artist_table.add_row(
                artist,
                artist_id,
                "Cache Update",
            )

        # Add processing records
        for result in results:
            if result.file_hash:
                # Before record
                before_table.add_row(
                    result.file_hash,
                    str(result.source_path),
                    str(result.metadata) if result.metadata else "N/A",
                )

                # After record
                after_table.add_row(
                    result.file_hash,
                    str(result.target_path) if result.target_path else "N/A",
                    "Success" if result.success else f"Error: {result.error_message}",
                )

        # Print tables if they have data
        if artists_seen:
            self.console.print(artist_table)
        self.console.print(before_table)
        self.console.print(after_table)

    def _show_summary(self, results: List[ProcessResult]) -> None:
        """Display a summary of processing results.

        Args:
            results: List of processing results.
        """
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        failed_count = total_count - success_count

        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"Total files to process: {total_count}")
        if total_count > 0:
            self.console.print(f"[green]Will succeed: {success_count}[/green]")
            if failed_count > 0:
                self.console.print(f"[red]Will fail: {failed_count}[/red]")
                for result in results:
                    if not result.success:
                        self.console.print(
                            f"[red]  • {result.source_path}: {result.error_message}[/red]"
                        ) 