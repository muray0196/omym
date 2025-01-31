"""Command line interface for OMYM."""

import sys
from collections.abc import Generator
from typing import Optional

from omym.ui.cli.args import process_args
from omym.ui.cli.commands import FileCommand, DirectoryCommand
from omym.utils.logger import logger
from omym.core.metadata.music_file_processor import MusicProcessor
from omym.ui.cli.display import PreviewDisplay, ProgressDisplay, ResultDisplay


def process_command(args_list: Optional[list[str]] = None) -> None:
    """Process command line arguments.

    Args:
        args_list: List of command line arguments (for testing).
    """
    try:
        # Process arguments
        args = process_args(args_list)

        if args.target_path is None:
            logger.error("Target path is required")
            sys.exit(1)

        # Create and execute appropriate command
        command = FileCommand(args) if args.music_path.is_file() else DirectoryCommand(args)

        # Execute command and check for failures
        results = command.execute()
        if any(not r.success for r in results):
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", str(e))
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    process_command()


if __name__ == "__main__":
    main()
