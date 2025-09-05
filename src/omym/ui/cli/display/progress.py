"""Progress display functionality for CLI."""

from pathlib import Path
from typing import final
from rich.progress import Progress

from omym.domain.metadata.music_file_processor import MusicProcessor, ProcessResult


@final
class ProgressDisplay:
    """Handles progress display in CLI."""

    def process_files_with_progress(
        self,
        processor: MusicProcessor,
        music_path: Path,
        interactive: bool = False,
    ) -> list[ProcessResult]:
        """Process multiple files with progress bar.

        Args:
            processor: Music file processor instance.
            music_path: Path to process.
            interactive: Whether to run in interactive mode.

        Returns:
            List of processing results.
        """
        # Get list of files to process
        files = [f for f in music_path.rglob("*") if f.is_file()]
        results: list[ProcessResult] = []

        with Progress() as progress:
            # Create the main task
            task = progress.add_task("[cyan]Processing files...", total=len(files))

            for file in files:
                # Update description with current file
                _ = progress.update(task, description=f"[cyan]Processing {file.name}...")

                # Process the file
                result = processor.process_file(file)
                results.append(result)

                # Update progress
                _ = progress.update(task, advance=1)

                # Handle interactive mode
                if interactive and not result.success:
                    # TODO: Implement interactive handling
                    pass

        return results
