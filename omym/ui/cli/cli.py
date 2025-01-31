"""Command line interface for OMYM."""

import sys
from typing import final

from omym.ui.cli.args import ArgumentParser
from omym.ui.cli.commands import FileCommand, DirectoryCommand
from omym.utils.logger import logger


@final
class CommandProcessor:
    """Command line interface processor."""

    @staticmethod
    def process_command(args_list: list[str] | None = None) -> None:
        """Process command line arguments.

        Args:
            args_list: List of command line arguments (for testing).
        """
        try:
            # Process arguments
            args = ArgumentParser.process_args(args_list)

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
    CommandProcessor.process_command()


if __name__ == "__main__":
    main()
