"""Path generation system for organizing music files."""

from pathlib import Path
from sqlite3 import Connection
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from omym.utils.logger import logger
from omym.db.dao_filter import FilterDAO, FilterHierarchy, FilterValue
from omym.db.dao_albums import AlbumDAO


@dataclass
class PathInfo:
    """Path information for a file.

    Attributes:
        file_hash: Hash of the file content.
        relative_path: Relative path where the file should be placed.
        warnings: List of warning messages related to path generation.
    """

    file_hash: str
    relative_path: Path
    warnings: List[str]


class PathGenerator:
    """Path generator for organizing music files."""

    def __init__(self, conn: Connection, base_path: Path):
        """Initialize path generator.

        Args:
            conn: SQLite database connection.
            base_path: Base path for organizing files.
        """
        self.conn = conn
        self.base_path = base_path
        self.filter_dao = FilterDAO(conn)
        self.album_dao = AlbumDAO(conn)

    def generate_paths(
        self, grouped_files: Optional[Dict[str, Dict[str, Optional[str]]]] = None
    ) -> List[PathInfo]:
        """Generate paths for all files.

        Args:
            grouped_files: Optional dictionary mapping file paths to metadata.
                If provided, uses this for path generation instead of filters.

        Returns:
            List[PathInfo]: List of path information for each file.
                Each PathInfo contains the file hash, relative path, and any warnings.
        """
        if grouped_files is not None:
            return self._generate_paths_from_groups(grouped_files)
        return self._generate_paths_from_filters()

    def _generate_paths_from_groups(
        self, grouped_files: Dict[str, Dict[str, Optional[str]]]
    ) -> List[PathInfo]:
        """Generate paths from grouped files.

        Args:
            grouped_files: Dictionary mapping file paths to metadata.

        Returns:
            List[PathInfo]: List of path information for each file.
        """
        paths: List[PathInfo] = []

        for file_path, metadata in grouped_files.items():
            warnings: List[str] = []
            relative_path = Path()

            # Build relative path components
            components: List[str] = []

            # Add album artist
            album_artist = metadata.get("album_artist") or metadata.get("artist")
            if not album_artist:
                warnings.append("Missing album artist")
                album_artist = "Unknown-Artist"
            components.append(album_artist)

            # Add year and album
            year = metadata.get("year", "0000")
            album = metadata.get("album", "Unknown-Album")
            components.append(f"{year}_{album}")

            # Build relative path
            for component in components:
                relative_path = relative_path / component

            # Create path info
            path_info = PathInfo(
                file_hash=file_path,  # Using file path as hash for now
                relative_path=relative_path,
                warnings=warnings,
            )
            paths.append(path_info)

        return paths

    def _generate_paths_from_filters(self) -> List[PathInfo]:
        """Generate paths using the filter system.

        Returns:
            List[PathInfo]: List of path information for each file.
        """
        paths: List[PathInfo] = []
        hierarchies = self.filter_dao.get_hierarchies()
        if not hierarchies:
            logger.error("No hierarchies found")
            return paths

        # Get all values for each hierarchy
        hierarchy_values: Dict[int, List[FilterValue]] = {}
        for hierarchy in hierarchies:
            values = self.filter_dao.get_values(hierarchy.id)
            hierarchy_values[hierarchy.id] = values

        # Group files by hierarchy values
        file_groups = self._group_files_by_hierarchies(hierarchies, hierarchy_values)

        # Generate paths for each group
        for group_values, file_hashes in file_groups.items():
            group_paths = self._generate_group_paths(
                hierarchies, group_values, file_hashes
            )
            paths.extend(group_paths)

        return paths

    def _group_files_by_hierarchies(
        self,
        hierarchies: List[FilterHierarchy],
        hierarchy_values: Dict[int, List[FilterValue]],
    ) -> Dict[Tuple[str, ...], Set[str]]:
        """Group files by hierarchy values.

        Args:
            hierarchies: List of filter hierarchies to group by.
            hierarchy_values: Dictionary mapping hierarchy IDs to their filter values.

        Returns:
            Dict[Tuple[str, ...], Set[str]]: Dictionary mapping hierarchy value tuples
                to sets of file hashes. Each tuple contains the values for each hierarchy
                in order.
        """
        groups: Dict[Tuple[str, ...], Set[str]] = {}

        # Get all file hashes
        file_hashes: Set[str] = set()
        for values in hierarchy_values.values():
            for value in values:
                file_hashes.add(value.file_hash)

        # Group files by hierarchy values
        for file_hash in file_hashes:
            group_key: List[str] = []
            for hierarchy in hierarchies:
                value = self._find_value_for_file(
                    hierarchy.id, file_hash, hierarchy_values[hierarchy.id]
                )
                if not value:
                    logger.warning(
                        "Missing value for hierarchy %s, file %s",
                        hierarchy.name,
                        file_hash,
                    )
                    break
                group_key.append(value)
            else:
                key = tuple(group_key)
                if key not in groups:
                    groups[key] = set()
                groups[key].add(file_hash)

        return groups

    def _find_value_for_file(
        self, hierarchy_id: int, file_hash: str, values: List[FilterValue]
    ) -> Optional[str]:
        """Find value for a file in a hierarchy.

        Args:
            hierarchy_id: ID of the hierarchy to search in.
            file_hash: Hash of the file to find value for.
            values: List of filter values to search through.

        Returns:
            Optional[str]: The value for the file in the hierarchy if found,
                None if not found.
        """
        for value in values:
            if value.hierarchy_id == hierarchy_id and value.file_hash == file_hash:
                return value.value
        return None

    def _generate_group_paths(
        self,
        hierarchies: List[FilterHierarchy],
        group_values: Tuple[str, ...],
        file_hashes: Set[str],
    ) -> List[PathInfo]:
        """Generate paths for a group of files.

        Args:
            hierarchies: List of filter hierarchies used for path generation.
            group_values: Tuple of values for each hierarchy in order.
            file_hashes: Set of file hashes to generate paths for.

        Returns:
            List[PathInfo]: List of path information for each file in the group.
                Each PathInfo contains the file hash, relative path, and any warnings.
        """
        paths: List[PathInfo] = []
        relative_path = Path()

        # Build relative path
        for value in group_values:
            relative_path = relative_path / value

        # Generate paths for each file
        for file_hash in file_hashes:
            warnings: List[str] = []
            path_info = PathInfo(
                file_hash=file_hash,
                relative_path=relative_path,
                warnings=warnings,
            )
            paths.append(path_info)

        return paths
