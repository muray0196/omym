"""Path generation system for organizing music files."""

from pathlib import Path
from sqlite3 import Connection
from typing import final
from dataclasses import dataclass

from omym.infra.logger.logger import logger
from omym.infra.db.daos.filter_dao import FilterDAO, FilterHierarchy, FilterValue
from omym.infra.db.daos.albums_dao import AlbumDAO


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
    warnings: list[str]


@final
class PathGenerator:
    """Path generator for organizing music files."""

    conn: Connection
    base_path: Path
    filter_dao: FilterDAO
    album_dao: AlbumDAO

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

    def generate_paths(self, grouped_files: dict[str, dict[str, str | None]] | None = None) -> list[PathInfo]:
        """Generate paths for all files.

        Args:
            grouped_files: Optional dictionary mapping file paths to metadata.
                If provided, uses this for path generation instead of filters.

        Returns:
            list[PathInfo]: List of path information for each file.
                Each PathInfo contains the file hash, relative path, and any warnings.
        """
        if grouped_files is not None:
            return self._generate_paths_from_groups(grouped_files)
        return self._generate_paths_from_filters()

    def _generate_paths_from_groups(self, grouped_files: dict[str, dict[str, str | None]]) -> list[PathInfo]:
        """Generate paths from grouped files.

        Args:
            grouped_files: Dictionary mapping file paths to metadata.

        Returns:
            list[PathInfo]: List of path information for each file.
        """
        paths: list[PathInfo] = []

        for file_path, metadata in grouped_files.items():
            warnings: list[str] = []
            components: list[str] = []

            # Add album artist.
            album_artist = metadata.get("album_artist") or metadata.get("artist")
            if not album_artist:
                warnings.append("Missing album artist")
                album_artist = "Unknown-Artist"
            components.append(album_artist)

            # Add year and album.
            year = metadata.get("year", "0000")
            album = metadata.get("album", "Unknown-Album")
            components.append(f"{year}_{album}")

            # Build relative path using the helper method.
            relative_path = self._assemble_relative_path(components)

            paths.append(
                PathInfo(
                    file_hash=file_path,  # Using file path as hash for now.
                    relative_path=relative_path,
                    warnings=warnings,
                )
            )

        return paths

    def _generate_paths_from_filters(self) -> list[PathInfo]:
        """Generate paths using the filter system.

        Returns:
            list[PathInfo]: List of path information for each file.
        """
        paths: list[PathInfo] = []
        hierarchies = self.filter_dao.get_hierarchies()
        if not hierarchies:
            logger.error("No hierarchies found")
            return paths

        # Get all values for each hierarchy.
        hierarchy_values: dict[int, list[FilterValue]] = {}
        for hierarchy in hierarchies:
            values = self.filter_dao.get_values(hierarchy.id)
            hierarchy_values[hierarchy.id] = values

        # Group files by hierarchy values.
        file_groups = self._group_files_by_hierarchies(hierarchies, hierarchy_values)

        # Generate paths for each group.
        for group_values, file_hashes in file_groups.items():
            group_paths = self._generate_group_paths(hierarchies, group_values, file_hashes)
            paths.extend(group_paths)

        return paths

    def _group_files_by_hierarchies(
        self,
        hierarchies: list[FilterHierarchy],
        hierarchy_values: dict[int, list[FilterValue]],
    ) -> dict[tuple[str, ...], set[str]]:
        """Group files by hierarchy values.

        Args:
            hierarchies: List of filter hierarchies to group by.
            hierarchy_values: Dictionary mapping hierarchy IDs to their filter values.

        Returns:
            dict[tuple[str, ...], set[str]]: Dictionary mapping hierarchy value tuples
                to sets of file hashes.
        """
        groups: dict[tuple[str, ...], set[str]] = {}

        # Get all file hashes.
        file_hashes: set[str] = set()
        for values in hierarchy_values.values():
            for value in values:
                file_hashes.add(value.file_hash)

        # Group files by hierarchy values.
        for file_hash in file_hashes:
            group_key: list[str] = []
            for hierarchy in hierarchies:
                value = self._find_value_for_file(hierarchy.id, file_hash, hierarchy_values[hierarchy.id])
                if not value:
                    logger.warning("Missing value for hierarchy %s, file %s", hierarchy.name, file_hash)
                    break
                group_key.append(value)
            else:
                key = tuple(group_key)
                groups.setdefault(key, set()).add(file_hash)

        return groups

    def _find_value_for_file(self, hierarchy_id: int, file_hash: str, values: list[FilterValue]) -> str | None:
        """Find value for a file in a hierarchy.

        Args:
            hierarchy_id: ID of the hierarchy to search in.
            file_hash: Hash of the file to find value for.
            values: List of filter values to search through.

        Returns:
            str | None: The value for the file in the hierarchy if found,
                None if not found.
        """
        for value in values:
            if value.hierarchy_id == hierarchy_id and value.file_hash == file_hash:
                return value.value
        return None

    def _generate_group_paths(
        self,
        hierarchies: list[FilterHierarchy],
        group_values: tuple[str, ...],
        file_hashes: set[str],
    ) -> list[PathInfo]:
        """Generate paths for a group of files.

        Args:
            hierarchies: List of filter hierarchies used for path generation.
            group_values: Tuple of values for each hierarchy in order.
            file_hashes: Set of file hashes to generate paths for.

        Returns:
            list[PathInfo]: List of path information for each file in the group.
        """
        # Build the relative path from group values, with logging for each hierarchy.
        relative_path = self._assemble_relative_path(list(group_values), hierarchies)
        paths: list[PathInfo] = []

        # Generate a PathInfo for each file in the group.
        for file_hash in file_hashes:
            paths.append(
                PathInfo(
                    file_hash=file_hash,
                    relative_path=relative_path,
                    warnings=[],
                )
            )

        return paths

    def _assemble_relative_path(self, components: list[str], hierarchies: list[FilterHierarchy] | None = None) -> Path:
        """Assemble a relative path from a list of components.

        If hierarchies are provided, logs each component with the corresponding hierarchy name.

        Args:
            components: List of path components.
            hierarchies: Optional list of FilterHierarchy for logging.

        Returns:
            Path: Assembled relative path.
        """
        if hierarchies:
            for i, component in enumerate(components):
                if i < len(hierarchies):
                    logger.debug("Using hierarchy %s with value %s", hierarchies[i].name, component)
        # Use the Path constructor to join components.
        return Path(*components)
