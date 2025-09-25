"""Command line interface for OMYM."""

import sys
from typing import final

from omym.features.restoration.domain.models import RestoreResult
from omym.ui.cli.args import ArgumentParser
from omym.ui.cli.args.options import CLIArgs, OrganizeArgs, RestoreArgs
from omym.ui.cli.commands import DirectoryCommand, FileCommand, RestoreCommand
from omym.platform.logging import logger


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
            args: CLIArgs = ArgumentParser.process_args(args_list)

            if isinstance(args, OrganizeArgs):
                command = (
                    FileCommand(args)
                    if args.music_path.is_file()
                    else DirectoryCommand(args)
                )
                results = command.execute()
                if any(not r.success for r in results):
                    sys.exit(1)
                return

            assert isinstance(args, RestoreArgs)
            results = RestoreCommand(args).execute()
            if CommandProcessor._has_restore_failures(results):
                sys.exit(1)
            return

        except KeyboardInterrupt:
            logger.info("\nOperation cancelled by user")
            sys.exit(130)
        except Exception as e:
            logger.error("An unexpected error occurred: %s", str(e))
            sys.exit(1)

    @staticmethod
    def _has_restore_failures(results: list[RestoreResult]) -> bool:
        """Determine whether a restore run encountered irrecoverable failures."""

        for result in results:
            if result.moved:
                continue
            if result.message in {"dry_run", "destination_exists"}:
                continue
            if result.message is None:
                continue
            return True
        return False


def main() -> int:
    """Main entry point.

    Returns:
        int: Process exit code (0 on success). Note that underlying
        command processing may call ``sys.exit(...)`` on errors, so this
        return is only reached when processing completes successfully.
    """
    CommandProcessor.process_command()
    return 0
