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
    """Organize files according to the specified format."""
    try:
        with DatabaseManager(":memory:") as db_manager:
            # Initialize components
            filter_dao = FilterDAO(db_manager)
            music_grouper = MusicGrouper()
            path_generator = PathGenerator(filter_dao)

            # Register hierarchies from format string
            filter_dao.register_hierarchies(format_str)

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
                        logger.warning(f"{source_path}: {warning}")

                if dry_run:
                    logger.info(f"Would move {source_path} to {target_path}")
                    continue

                if target_path.exists() and not force:
                    logger.warning(
                        f"Skipping {source_path}: Target exists {target_path}"
                    )
                    continue

                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Move the file
                try:
                    if force and target_path.exists():
                        target_path.unlink()
                    shutil.move(str(source_path), str(target_path))
                    logger.info(f"Moved {source_path} to {target_path}")
                except Exception as e:
                    logger.error(f"Failed to move {source_path}: {e}")
                    return 1

            return 0

    except Exception as e:
        logger.error(f"Failed to organize files: {e}")
        return 1
