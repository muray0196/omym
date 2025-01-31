"""Directory command execution."""

from typing import override

from omym.core.metadata.music_file_processor import ProcessResult
from omym.ui.cli.commands.executor import CommandExecutor


class DirectoryCommand(CommandExecutor):
    """Command for processing a directory."""

    @override
    def execute(self) -> list[ProcessResult]:
        """Execute directory processing command.

        Returns:
            List of processing results.
        """
        results = self.progress_display.process_files_with_progress(
            self.processor,
            self.args.music_path,
            interactive=self.args.interactive,
        )
        self.display_results(results)
        return results
