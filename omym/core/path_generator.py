"""Path generation system for organizing music files."""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from omym.utils.logger import logger
from omym.core.filtering import FilterDAO, FilterHierarchy, FilterValue
from omym.db.dao_albums import AlbumDAO, AlbumInfo, TrackPosition


@dataclass
class PathInfo:
    """Path information."""

    file_hash: str
    relative_path: Path
    warnings: List[str]


class PathGenerator:
    """Path generator for organizing music files."""

    def __init__(self, conn, base_path: Path):
        """Initialize path generator.

        Args:
            conn: Database connection.
            base_path: Base path for organizing files.
        """
        self.conn = conn
        self.base_path = base_path
        self.filter_dao = FilterDAO(conn)
        self.album_dao = AlbumDAO(conn)

    def generate_paths(self) -> List[PathInfo]:
        """Generate paths for all files.

        Returns:
            List[PathInfo]: List of path information.
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
    ) -> Dict[tuple, Set[str]]:
        """Group files by hierarchy values.

        Args:
            hierarchies: List of hierarchies.
            hierarchy_values: Dictionary of hierarchy values.

        Returns:
            Dict[tuple, Set[str]]: Dictionary mapping hierarchy value tuples to file hashes.
        """
        groups: Dict[tuple, Set[str]] = {}

        # Get all file hashes
        file_hashes: Set[str] = set()
        for values in hierarchy_values.values():
            for value in values:
                file_hashes.add(value.file_hash)

        # Group files by hierarchy values
        for file_hash in file_hashes:
            group_key = []
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
            hierarchy_id: Hierarchy ID.
            file_hash: File hash.
            values: List of filter values.

        Returns:
            Optional[str]: Value if found.
        """
        for value in values:
            if value.hierarchy_id == hierarchy_id and value.file_hash == file_hash:
                return value.value
        return None

    def _generate_group_paths(
        self,
        hierarchies: List[FilterHierarchy],
        group_values: tuple,
        file_hashes: Set[str],
    ) -> List[PathInfo]:
        """Generate paths for a group of files.

        Args:
            hierarchies: List of hierarchies.
            group_values: Tuple of hierarchy values.
            file_hashes: Set of file hashes.

        Returns:
            List[PathInfo]: List of path information.
        """
        paths: List[PathInfo] = []

        # Build relative path
        relative_path = Path()
        for value in group_values:
            relative_path = relative_path / value

        # Generate paths for each file
        for file_hash in file_hashes:
            warnings = []
            path_info = PathInfo(
                file_hash=file_hash,
                relative_path=relative_path,
                warnings=warnings,
            )
            paths.append(path_info)

        return paths
