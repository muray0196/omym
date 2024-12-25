"""Organize command implementation."""

import logging
import shutil
from pathlib import Path

from omym.core.music_grouper import MusicGrouper
from omym.core.path_generator import PathGenerator
from omym.db.dao_filter import FilterDAO
from omym.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def organize_files(
    path: Path,
    format_str: str,
    target_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Organize files according to the specified format.

    Args:
        path: Path to file or directory to process.
        format_str: Format string specifying the organization structure.
        target_dir: Base directory for organized files.
        dry_run: If True, only show what would be done without moving files.
        force: If True, overwrite existing files at target paths.

    Returns:
        int: Exit code (0 for success, 1 for failure).

    Note:
        Uses an in-memory database for organizing operations to avoid
        modifying the actual database.
    """
    try:
        # Use None for db_path to create in-memory database
        with DatabaseManager(db_path=None) as db_manager:
            if not db_manager.conn:
                logger.error("Failed to connect to in-memory database")
                return 1

            # Initialize components
            filter_dao = FilterDAO(db_manager.conn)
            music_grouper = MusicGrouper()
            path_generator = PathGenerator(db_manager.conn, base_path=target_dir)

            # Register hierarchies from format string
            hierarchies = format_str.split("/")
            for hierarchy in hierarchies:
                if hierarchy.strip():
                    filter_dao.insert_hierarchy(
                        hierarchy.strip(), priority=len(filter_dao.get_hierarchies())
                    )

            # Process files and generate paths
            if path.is_file():
                files = [path]
            else:
                files = [f for f in path.rglob("*") if f.is_file()]

            # Group files and generate paths
            grouped_files = music_grouper.group_by_path_format(files, format_str)
            path_infos = path_generator.generate_paths(grouped_files)

            # Process each file
            for info in path_infos:
                source_path = Path(info.file_hash)  # Need to get actual source path
                target_path = target_dir / info.relative_path

                if info.warnings:
                    for warning in info.warnings:
                        logger.warning("%s: %s", source_path, warning)

                if dry_run:
                    logger.info("Would move %s to %s", source_path, target_path)
                    continue

                if target_path.exists() and not force:
                    logger.warning(
                        "Skipping %s: Target exists %s", source_path, target_path
                    )
                    continue

                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Move the file
                try:
                    if force and target_path.exists():
                        target_path.unlink()
                    shutil.move(str(source_path), str(target_path))
                    logger.info("Moved %s to %s", source_path, target_path)
                except Exception as e:
                    logger.error("Failed to move %s: %s", source_path, e)
                    return 1

            return 0

    except Exception as e:
        logger.error("Failed to organize files: %s", e)
        return 1
