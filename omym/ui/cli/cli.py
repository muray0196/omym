"""Command line interface for OMYM."""

import sys
from typing import Optional, List

from omym.core.metadata.music_file_processor import MusicProcessor
from omym.ui.cli.args import process_args
from omym.ui.cli.display.preview import PreviewDisplay
from omym.ui.cli.display.progress import ProgressDisplay
from omym.ui.cli.display.result import ResultDisplay
from omym.utils.logger import logger


def process_command(args_list: Optional[List[str]] = None) -> None:
    """Process command line arguments.

    Args:
        args_list: List of command line arguments (for testing).
    """
    # Process arguments
    args = process_args(args_list)

    if args.target_path is None:
        logger.error("Target path is required")
        sys.exit(1)

    # Create processor with appropriate base path
    processor = MusicProcessor(
        base_path=args.target_path,
        dry_run=args.dry_run,
    )

    # Initialize display managers
    preview_display = PreviewDisplay()
    progress_display = ProgressDisplay()
    result_display = ResultDisplay()

    try:
        if args.music_path.is_file():
            results = [processor.process_file(args.music_path)]
        else:
            # Process files with progress bar
            results = progress_display.process_files_with_progress(
                processor,
                args.music_path,
                interactive=args.interactive,
            )

        # Display preview in dry-run mode
        if args.dry_run:
            preview_display.show_preview(results, processor.base_path, show_db=args.show_db)
        # Display normal results otherwise
        else:
            result_display.show_results(results, quiet=args.quiet)

        # Exit with error code if any failures
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
