"""Command line argument parser."""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import final

from omym.infra.logger.logger import logger, setup_logger
from omym.config.config import Config
from omym.domain.restoration import CollisionPolicy
from omym.ui.cli.args.options import CLIArgs, OrganizeArgs, RestoreArgs


@final
class ArgumentParser:
    """Command line argument parser."""

    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create argument parser.

        Returns:
            argparse.ArgumentParser: Configured argument parser.
        """
        parser = argparse.ArgumentParser(
            description="OMYM (Organize My Music) - A tool to organize and restore music libraries.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        subparsers = parser.add_subparsers(dest="command", required=True)

        organize_parser = subparsers.add_parser(
            "organize",
            help="Organize a file or directory into the target structure",
        )
        _ = organize_parser.add_argument(
            "music_path",
            type=str,
            help="Path to music file or directory to process",
            metavar="MUSIC_PATH",
        )
        _ = organize_parser.add_argument(
            "--target",
            type=str,
            help="Target directory for organized files (defaults to music_path)",
            metavar="TARGET_PATH",
        )
        _ = organize_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )
        _ = organize_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed processing information",
        )
        _ = organize_parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress all output except errors",
        )
        _ = organize_parser.add_argument(
            "--force",
            action="store_true",
            help="Override safety checks",
        )
        _ = organize_parser.add_argument(
            "--interactive",
            action="store_true",
            help="Enable interactive mode",
        )
        _ = organize_parser.add_argument(
            "--db",
            action="store_true",
            help="Enable database operations preview",
        )
        _ = organize_parser.add_argument(
            "--clear-artist-cache",
            action="store_true",
            help="Clear cached artist IDs before processing",
        )
        _ = organize_parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Clear all caches and processing state before processing",
        )

        restore_parser = subparsers.add_parser(
            "restore",
            help="Restore files that were previously organized by OMYM",
        )
        _ = restore_parser.add_argument(
            "source_root",
            type=str,
            help="Root directory that currently holds the organized files",
            metavar="SOURCE_ROOT",
        )
        _ = restore_parser.add_argument(
            "--destination-root",
            type=str,
            help="Optional destination root to place restored files",
            metavar="DESTINATION_ROOT",
        )
        _ = restore_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview restore actions without moving files",
        )
        _ = restore_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed restoration information",
        )
        _ = restore_parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress all output except errors",
        )
        _ = restore_parser.add_argument(
            "--collision-policy",
            type=str,
            default=CollisionPolicy.ABORT.value,
            metavar="POLICY",
            help="How to handle destination collisions (abort, skip, backup)",
        )
        _ = restore_parser.add_argument(
            "--backup-suffix",
            type=str,
            default=".bak",
            help="Suffix used when backing up colliding destinations",
        )
        _ = restore_parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continue restoring even if an error occurs",
        )
        _ = restore_parser.add_argument(
            "--limit",
            type=int,
            help="Process only the first N records matching the criteria",
        )
        _ = restore_parser.add_argument(
            "--purge-state",
            action="store_true",
            help="Clear cached processing state after a successful restore",
        )

        return parser

    @staticmethod
    def process_args(args_list: Sequence[str] | None = None) -> CLIArgs:
        """Process command line arguments.

        Args:
            args_list: List of command line arguments (for testing).

        Returns:
            Args: Processed command line arguments.

        Raises:
            SystemExit: If required paths don't exist or other validation fails.
        """
        parser = ArgumentParser.create_parser()
        parsed_args = parser.parse_args(args_list)

        # Set log level based on verbosity flags
        if parsed_args.quiet:
            log_level = logging.ERROR
        elif parsed_args.verbose:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        _ = setup_logger(console_level=log_level)

        command: str = parsed_args.command

        if command == "organize":
            return ArgumentParser._process_organize(parsed_args)

        if command == "restore":
            return ArgumentParser._process_restore(parsed_args)

        logger.error("Unsupported command: %s", command)
        sys.exit(2)

    @staticmethod
    def _process_organize(parsed_args: argparse.Namespace) -> OrganizeArgs:
        music_path = Path(parsed_args.music_path)
        if not music_path.exists():
            logger.error("Music path does not exist: %s", music_path)
            sys.exit(1)

        if parsed_args.target:
            target_path = Path(parsed_args.target)
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path = music_path.parent if music_path.is_file() else music_path

        _ = Config.load()

        return OrganizeArgs(
            command="organize",
            music_path=music_path,
            target_path=target_path,
            dry_run=parsed_args.dry_run,
            verbose=parsed_args.verbose,
            quiet=parsed_args.quiet,
            force=parsed_args.force,
            interactive=parsed_args.interactive,
            show_db=parsed_args.db,
            clear_artist_cache=parsed_args.clear_artist_cache,
            clear_cache=parsed_args.clear_cache,
        )

    @staticmethod
    def _process_restore(parsed_args: argparse.Namespace) -> RestoreArgs:
        source_root = Path(parsed_args.source_root)
        if not source_root.exists() or not source_root.is_dir():
            logger.error("Source root does not exist or is not a directory: %s", source_root)
            sys.exit(1)

        destination_root = (
            Path(parsed_args.destination_root).resolve()
            if parsed_args.destination_root
            else None
        )

        _ = Config.load()

        collision_policy = CollisionPolicy.from_user_input(parsed_args.collision_policy)

        limit = parsed_args.limit
        if limit is not None and limit <= 0:
            logger.error("Limit must be a positive integer; received %s", limit)
            sys.exit(1)

        return RestoreArgs(
            command="restore",
            source_root=source_root.resolve(),
            destination_root=destination_root,
            dry_run=parsed_args.dry_run,
            verbose=parsed_args.verbose,
            quiet=parsed_args.quiet,
            collision_policy=collision_policy,
            backup_suffix=parsed_args.backup_suffix,
            continue_on_error=parsed_args.continue_on_error,
            limit=limit,
            purge_state=parsed_args.purge_state,
        )
