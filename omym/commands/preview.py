"""Preview command implementation."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from omym.core.music_grouper import MusicGrouper
from omym.core.path_generator import PathGenerator, PathInfo
from omym.db.dao_filter import FilterDAO
from omym.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def format_text_output(path_infos: List[PathInfo]) -> str:
    """Format path information as text."""
    output = []
    for info in path_infos:
        line = f"{info.file_hash}: {info.relative_path}"
        if info.warnings:
            line += f"\n  Warnings: {', '.join(info.warnings)}"
        output.append(line)
    return "\n".join(output)


def format_json_output(path_infos: List[PathInfo]) -> str:
    """Format path information as JSON."""
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
    output_format: str = "text",
) -> int:
    """Preview how files would be organized."""
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

            # Format and output results
            if output_format == "json":
                output = format_json_output(path_infos)
            else:
                output = format_text_output(path_infos)

            print(output)
            return 0

    except Exception as e:
        logger.error(f"Failed to preview files: {e}")
        return 1
