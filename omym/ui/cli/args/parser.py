"""Command line argument parser."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, List

from omym.utils.logger import logger, setup_logger
from omym.config import Config
from omym.ui.cli.args.options import Args


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="OMYM (Organize My Music) - A tool to organize your music library based on metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required positional argument for music path
    parser.add_argument(
        "music_path",
        type=str,
        help="Path to music file or directory to process",
        metavar="MUSIC_PATH",
    )

    # Optional target path
    parser.add_argument(
        "--target",
        type=str,
        help="Target directory for organized files (defaults to music_path)",
        metavar="TARGET_PATH",
    )

    # Common options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed processing information",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override safety checks",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Enable database operations preview",
    )

    return parser


def process_args(args_list: Optional[List[str]] = None) -> Args:
    """Process command line arguments.

    Args:
        args_list: List of command line arguments (for testing).

    Returns:
        Args: Processed command line arguments.

    Raises:
        SystemExit: If required paths don't exist or other validation fails.
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args_list)

    # Set log level based on verbosity flags
    if parsed_args.quiet:
        log_level = logging.ERROR
    elif parsed_args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    setup_logger(console_level=log_level)

    # Convert paths to Path objects and verify they exist
    music_path = Path(parsed_args.music_path)
    if not music_path.exists():
        logger.error("Music path does not exist: %s", music_path)
        sys.exit(1)

    # Set target path based on input type
    target_path = None
    if parsed_args.target:
        target_path = Path(parsed_args.target)
        target_path.mkdir(parents=True, exist_ok=True)
    else:
        target_path = music_path.parent if music_path.is_file() else music_path

    # Load configuration
    config_path = None
    if parsed_args.config:
        config_path = Path(parsed_args.config)
        Config.load(config_path)
    else:
        Config.load()  # Load default config

    return Args(
        music_path=music_path,
        target_path=target_path,
        dry_run=parsed_args.dry_run,
        verbose=parsed_args.verbose,
        quiet=parsed_args.quiet,
        force=parsed_args.force,
        interactive=parsed_args.interactive,
        config_path=config_path,
        show_db=parsed_args.db,
    ) 