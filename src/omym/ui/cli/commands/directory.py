"""src/omym/ui/cli/commands/directory.py
What: Execute organise runs for directory roots via the CLI.
Why: Bridge parsed arguments with application services for bulk processing.
"""

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
        summary = self.calculate_unprocessed_pending(self.args.music_path, results)
        self.result_display.show_unprocessed_summary(summary, quiet=self.args.quiet)
        return results
