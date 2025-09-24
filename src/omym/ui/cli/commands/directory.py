"""Directory command execution."""

from typing import override

from omym.features.metadata import ProcessResult
from omym.ui.cli.commands.executor import CommandExecutor


class DirectoryCommand(CommandExecutor):
    """Command for processing a directory."""

    @override
    def execute(self) -> list[ProcessResult]:
        """Execute directory processing command.

        Returns:
            List of processing results.
        """
        results = self.progress_display.run_with_service(
            self.app,
            self.request,
            self.args.music_path,
            interactive=self.args.interactive,
        )
        self.display_results(results)
        return results
