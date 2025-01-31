"""File command execution."""

from typing import override

from omym.core.metadata.music_file_processor import ProcessResult
from omym.ui.cli.commands.executor import CommandExecutor


class FileCommand(CommandExecutor):
    """Command for processing a single file."""

    @override
    def execute(self) -> list[ProcessResult]:
        """Execute file processing command.

        Returns:
            List of processing results.
        """
        results = [self.processor.process_file(self.args.music_path)]
        self.display_results(results)
        return results
