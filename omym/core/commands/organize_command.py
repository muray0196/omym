"""File organization operations."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from omym.core.organization.group_manager import MusicGrouper
from omym.core.path.path_generator import PathGenerator
from omym.db.daos.filter_dao import FilterDAO
from omym.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def organize_files(
    path: Path,
    format_str: str,
    target_dir: Optional[Path] = None,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Organize files according to the specified format.

    Args:
        path: Path to file or directory to process.
        format_str: Format string specifying the organization structure.
        target_dir: Optional base directory for organized files. If None, uses input path.
        dry_run: If True, only show what would be done without moving files.
        force: If True, overwrite existing files at target paths.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    try:
        # Use input path as target directory if not specified
        if target_dir is None:
            target_dir = path if path.is_dir() else path.parent

        # Use persistent database for caching
        project_root = Path(__file__).parent.parent.parent.parent
        db_dir = project_root / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "omym.db"

        with DatabaseManager(db_path=db_path) as db_manager:
            if not db_manager.conn:
                logger.error("Failed to connect to database")
                return 1

            # Initialize components
            filter_dao = FilterDAO(db_manager.conn)
            music_grouper = MusicGrouper()
            path_generator = PathGenerator(db_manager.conn, base_path=target_dir)

            # Begin transaction
            db_manager.begin_transaction()
            try:
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
                    source_path = Path(info.file_hash)  # file_hash contains the actual source path
                    target_path = target_dir / info.relative_path

                    if info.warnings:
                        for warning in info.warnings:
                            logger.warning("%s: %s", source_path, warning)

                    if dry_run:
                        logger.info("Would move %s to %s", source_path, target_path)
                        continue

                    if target_path.exists() and not force:
                        logger.warning("Skipping %s: Target exists %s", source_path, target_path)
                        continue

                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Move the file
                    try:
                        if force and target_path.exists():
                            target_path.unlink()
                        shutil.move(str(source_path), str(target_path))
                    except Exception as e:
                        logger.error("Failed to move %s: %s", source_path, e)
                        db_manager.rollback_transaction()
                        return 1

                    logger.info("Moving file from %s to %s", source_path, target_path)

                # Commit transaction if all operations succeeded
                db_manager.commit_transaction()
                return 0

            except Exception as e:
                db_manager.rollback_transaction()
                logging.error("Transaction failed: %s", e)
                raise

    except Exception as e:
        logger.error("Failed to organize files: %s", e)
        return 1 