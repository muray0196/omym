"""Command line interface for OMYM."""

import argparse
import logging
from pathlib import Path
from typing import Optional

from omym.commands.organize import organize_files
from omym.commands.preview import preview_files

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Organize Your Music (OMYM) - A tool to organize music files."
    )

    # Common arguments
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the music file or directory to process",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="AlbumArtist/Album/[%02d] %title",
        help="Format string for organizing files (default: %(default)s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Preview command
    preview_parser = subparsers.add_parser(
        "preview",
        help="Preview how files would be organized without making changes",
    )
    preview_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format for preview results (default: %(default)s)",
    )

    # Organize command
    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize files according to the specified format",
    )
    organize_parser.add_argument(
        "--target-dir",
        type=Path,
        required=True,
        help="Target directory for organized files",
    )
    organize_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    organize_parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite of existing files",
    )

    return parser


def setup_logging(verbose: bool, quiet: bool) -> None:
    """Set up logging configuration."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    setup_logging(parsed_args.verbose, parsed_args.quiet)

    try:
        if parsed_args.command == "preview":
            return preview_files(
                path=parsed_args.path,
                format_str=parsed_args.format,
                output_format=parsed_args.output_format,
            )
        elif parsed_args.command == "organize":
            return organize_files(
                path=parsed_args.path,
                format_str=parsed_args.format,
                target_dir=parsed_args.target_dir,
                dry_run=parsed_args.dry_run,
                force=parsed_args.force,
            )
        else:
            parser.print_help()
            return 1

    except Exception as e:
        logger.error(str(e))
        if parsed_args.verbose:
            logger.exception("Detailed error information:")
        return 1

    return 0
