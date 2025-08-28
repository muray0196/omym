"""Command line argument options."""

from dataclasses import dataclass
from pathlib import Path
from typing import final


@final
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
        clear_artist_cache: Clear cached artist IDs before processing.
        clear_cache: Clear all caches and processing state.
    """

    music_path: Path
    target_path: Path | None = None
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    force: bool = False
    interactive: bool = False
    config_path: Path | None = None
    show_db: bool = False
    clear_artist_cache: bool = False
    clear_cache: bool = False
