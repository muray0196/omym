"""Command line argument options."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, final

from omym.features.restoration.domain.models import CollisionPolicy


@final
@dataclass(slots=True)
class OrganizeArgs:
    """Command line arguments for the ``organize`` or ``plan`` subcommands."""

    command: Literal["organize", "plan"]
    music_path: Path
    target_path: Path
    dry_run: bool
    verbose: bool
    quiet: bool
    force: bool
    interactive: bool
    show_db: bool
    clear_artist_cache: bool
    clear_cache: bool


@final
@dataclass(slots=True)
class RestoreArgs:
    """Command line arguments for the ``restore`` subcommand."""

    command: Literal["restore"]
    source_root: Path
    destination_root: Path | None
    dry_run: bool
    verbose: bool
    quiet: bool
    collision_policy: CollisionPolicy
    backup_suffix: str
    continue_on_error: bool
    limit: int | None
    purge_state: bool


@final
@dataclass(slots=True)
class PreferencesArgs:
    """Command line arguments for the ``preferences`` subcommand."""

    command: Literal["preferences"]
    show_all: bool
    only_missing: bool


CLIArgs = OrganizeArgs | RestoreArgs | PreferencesArgs

__all__ = ["CLIArgs", "OrganizeArgs", "PreferencesArgs", "RestoreArgs"]
