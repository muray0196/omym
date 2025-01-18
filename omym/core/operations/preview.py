"""Preview operations for file organization."""

import json
import logging
from pathlib import Path
from typing import List, Literal

from omym.core.music_grouper import MusicGrouper
from omym.core.path_generator import PathGenerator, PathInfo
from omym.db.dao_filter import FilterDAO
from omym.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def format_text_output(path_infos: List[PathInfo]) -> str:
    """Format path information as text.

    Args:
        path_infos: List of path information objects to format.

    Returns:
        str: Formatted text output with one line per file, including:
            - File hash and relative path
            - Any warnings indented on the next line
    """
    output: List[str] = []
    for info in path_infos:
        line = f"{info.file_hash}: {info.relative_path}"
        if info.warnings:
            line += f"\n  Warnings: {', '.join(info.warnings)}"
        output.append(line)
    return "\n".join(output)


def format_json_output(path_infos: List[PathInfo]) -> str:
    """Format path information as JSON.

    Args:
        path_infos: List of path information objects to format.

    Returns:
        str: JSON-formatted string containing an array of objects with:
            - file_hash: The file's content hash
            - relative_path: The target path relative to base directory
            - warnings: List of warning messages, if any
    """
    data = [
        {
            "file_hash": info.file_hash,
            "relative_path": str(info.relative_path),
            "warnings": info.warnings,
        }
        for info in path_infos
    ]
    return json.dumps(data, indent=2)


def preview_files(
    path: Path,
    format_str: str,
    output_format: Literal["text", "json"] = "text",
) -> int:
    """Preview how files would be organized.

    Args:
        path: Path to file or directory to process.
        format_str: Format string specifying the organization structure.
        output_format: Output format, either "text" or "json".

    Returns:
        int: Exit code (0 for success, 1 for failure).

    Note:
        Uses an in-memory database for preview operations to avoid
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
            path_generator = PathGenerator(db_manager.conn, base_path=path)

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

            # Format and output results
            if output_format == "json":
                output = format_json_output(path_infos)
            else:
                output = format_text_output(path_infos)

            print(output)
            return 0

    except Exception as e:
        logger.error("Failed to preview files: %s", e)
        return 1 