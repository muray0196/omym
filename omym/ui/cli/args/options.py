"""Command line argument options."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Args:
    """Command line arguments data class.

    Attributes:
        music_path: Path to music file or directory to process.
        target_path: Target directory for organized files.
        dry_run: Preview changes without applying them.
        verbose: Show detailed processing information.
        quiet: Suppress all output except errors.
        force: Override safety checks.
        interactive: Enable interactive mode.
        config_path: Path to custom configuration file.
        show_db: Enable database operations preview.
    """

    music_path: Path
    target_path: Optional[Path] = None
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    force: bool = False
    interactive: bool = False
    config_path: Optional[Path] = None
    show_db: bool = False 