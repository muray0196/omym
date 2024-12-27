"""Command line interface for OMYM."""

import argparse
import logging
from pathlib import Path
from typing import Optional, List, Dict
import sys
from rich.console import Console
from rich.tree import Tree
from rich.table import Table

from omym.core.processor import MusicProcessor, ProcessResult
from omym.utils.logger import logger, setup_logger
from omym.config import Config


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="OMYM (Organize My Music) - A tool to organize your music library based on metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common arguments for all commands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    common_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed processing information",
    )
    common_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    common_parser.add_argument(
        "--force",
        action="store_true",
        help="Override safety checks",
    )
    common_parser.add_argument(
        "--config",
        type=str,
        help="Path to custom configuration file",
        metavar="FILE",
    )
    common_parser.add_argument(
        "--db",
        action="store_true",
        help="Enable database operations preview",
    )

    # Process command - for single files
    process_parser = subparsers.add_parser(
        "process",
        help="Process a single music file",
        parents=[common_parser],
    )
    process_parser.add_argument(
        "path",
        type=str,
        help="Path to the music file to process",
        metavar="FILE",
    )

    # Organize command - for directories
    organize_parser = subparsers.add_parser(
        "organize",
        help="Process all music files in a directory",
        parents=[common_parser],
    )
    organize_parser.add_argument(
        "path",
        type=str,
        help="Directory containing music files to organize",
        metavar="DIR",
    )

    # Verify command - check without changes
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify file organization without changes",
        parents=[common_parser],
    )
    verify_parser.add_argument(
        "path",
        type=str,
        help="Directory to verify",
        metavar="DIR",
    )

    return parser


def display_db_preview(results: List[ProcessResult]) -> None:
    """Display a preview of database operations.

    Args:
        results: List of processing results.
    """
    console = Console()
    console.print("\n[bold magenta]Database Operations Preview:[/bold magenta]")

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
    artists_seen: Dict[str, str] = {}  # artist_name -> artist_id
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
        console.print(artist_table)
    console.print(before_table)
    console.print(after_table)


def display_preview(results: List[ProcessResult], base_path: Path, show_db: bool = False) -> None:
    """Display a preview of the planned file organization.

    Args:
        results: List of processing results.
        base_path: Base path for the music library.
        show_db: Whether to show database operations preview.
    """
    console = Console()
    console.print("\n[bold cyan]Preview of planned changes:[/bold cyan]")

    # Create a tree structure for visualization
    tree = Tree(f"📁 {base_path}")
    current_artist = None
    current_album = None
    artist_node = None
    album_node = None

    # Sort results by target path to group by artist/album
    sorted_results = sorted([r for r in results if r.target_path], key=lambda r: str(r.target_path))

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
    console.print(tree)

    # Show database operations if requested
    if show_db:
        display_db_preview(results)

    # Print summary
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    failed_count = total_count - success_count

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"Total files to process: {total_count}")
    if total_count > 0:
        console.print(f"[green]Will succeed: {success_count}[/green]")
        if failed_count > 0:
            console.print(f"[red]Will fail: {failed_count}[/red]")
            for result in results:
                if not result.success:
                    console.print(f"[red]  • {result.source_path}: {result.error_message}[/red]")


def process_files_with_progress(
    processor: MusicProcessor,
    path: Path,
    interactive: bool = True,
) -> List[ProcessResult]:
    """Process files with progress bar.

    Args:
        processor: Music processor instance.
        path: Path to process.
        interactive: Whether to run in interactive mode.

    Returns:
        List of ProcessResult objects.
    """
    # Create console with custom settings
    console = Console(force_terminal=True)

    # Count total files
    total_files = sum(
        1
        for f in path.rglob("*")
        if f.is_file() and f.suffix.lower() in processor.SUPPORTED_EXTENSIONS
    )

    # Create a counter for processed files
    processed_files = 0

    def update_progress(current: int, total: int) -> None:
        """Update progress counter.

        Args:
            current: Current number of files processed.
            total: Total number of files to process.
        """
        nonlocal processed_files
        if current > processed_files:
            processed_files = current
            if total_files > 0:
                # Create progress message
                progress = f"[{processed_files}/{total_files}]"
                # Print progress at the end of the current line
                console.print(progress, end="\r")

    # Process files
    results = processor.process_directory(path, update_progress)

    # Clear the progress line
    if total_files > 0:
        console.print(" " * 20, end="\r")  # Clear any remaining progress display

    return results


def process_command(args_list: Optional[List[str]] = None) -> None:
    """Process command line arguments.

    Args:
        args_list: List of command line arguments (for testing).
    """
    parser = create_parser()
    args = parser.parse_args(args_list)

    # Set log level based on verbosity flags
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    setup_logger(console_level=log_level)

    # Convert path to Path and verify it exists
    path = Path(args.path)
    if not path.exists():
        logger.error("Path does not exist: %s", path)
        sys.exit(1)

    # Load configuration
    if args.config:
        Config.load(Path(args.config))
    else:
        Config.load()  # Load default config

    # Create processor with appropriate base path
    processor = MusicProcessor(
        base_path=path.parent if args.command == "process" else path,
        dry_run=args.dry_run or args.command == "verify",
    )

    try:
        if args.command == "process":
            if not path.is_file():
                logger.error("Path must be a file for 'process' command: %s", path)
                sys.exit(1)
            results = [processor.process_file(path)]
        else:  # organize or verify
            if not path.is_dir():
                logger.error("Path must be a directory for '%s' command: %s", args.command, path)
                sys.exit(1)

            # Process files with progress bar
            results = process_files_with_progress(
                processor,
                path,
                interactive=not (args.quiet or args.dry_run or args.force),
            )

        # Display preview in dry-run mode
        if args.dry_run or args.command == "verify":
            display_preview(results, processor.base_path, show_db=args.db)
        # Display normal results otherwise
        elif not args.quiet:
            console = Console()
            console.print("\n[bold]Processing Summary:[/bold]")
            console.print(f"Total files processed: {len(results)}")
            console.print(f"[green]Successful: {sum(1 for r in results if r.success)}[/green]")
            console.print(f"[red]Failed: {sum(1 for r in results if not r.success)}[/red]")

        # Exit with error code if any failures
        if any(not r.success for r in results):
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", str(e))
        sys.exit(1)


def main():
    """Main entry point."""
    process_command()


if __name__ == "__main__":
    main()
