"""src/omym/ui/cli/commands/file.py
What: Execute organise runs targeting a single file via the CLI.
Why: Let users process individual tracks without rewriting orchestration.
"""

from typing import override

from omym.features.metadata import ProcessResult
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
        pending_total = self.calculate_unprocessed_pending(self.args.music_path.parent, results)
        self.result_display.show_unprocessed_total(pending_total, quiet=self.args.quiet)
        return results
