"""Path generation use cases.

Where: features/path/usecases.
What: Assemble relative library paths from filter hierarchies or grouped metadata.
Why: Expose a port-driven service so adapters can back persistence lookups.
"""

from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection
from typing import final

from omym.platform.db.daos.filter_dao import FilterDAO
from omym.platform.logging.logger import logger

from .ports import FilterHierarchyRecord, FilterQueryPort, FilterValueRecord


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

    base_path: Path
    _filters: FilterQueryPort

    def __init__(
        self,
        conn: Connection | None,
        base_path: Path,
        *,
        filter_gateway: FilterQueryPort | None = None,
    ) -> None:
        """Initialize path generator.

        Args:
            conn: Legacy SQLite database connection used when no port is supplied.
            base_path: Base path for organizing files.
            filter_gateway: Port that exposes filter hierarchy queries.
        """
        self.base_path = base_path
        if filter_gateway is not None:
            self._filters = filter_gateway
        elif conn is not None:
            self._filters = _FilterDaoAdapter(conn)
        else:
            raise ValueError("PathGenerator requires filter_gateway or conn")

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

        # First pass: compute album-level earliest year (ignore 0/invalid)
        album_earliest_year: dict[tuple[str, str], int] = {}
        for _file_path, metadata in grouped_files.items():
            album_artist = metadata.get("album_artist") or "Unknown-Artist"
            album = metadata.get("album") or "Unknown-Album"
            key = (album_artist, album)
            year_str = metadata.get("year")
            try:
                year_val = int(year_str) if year_str is not None else 0
            except ValueError:
                year_val = 0
            if year_val <= 0:
                continue
            current = album_earliest_year.get(key)
            if current is None or year_val < current:
                album_earliest_year[key] = year_val

        # Second pass: build paths using album-level earliest year
        for file_path, metadata in grouped_files.items():
            warnings: list[str] = []
            components: list[str] = []

            # Add album artist (no fallback to artist)
            album_artist = metadata.get("album_artist")
            if not album_artist:
                warnings.append("Missing album artist")
                album_artist = "Unknown-Artist"
            components.append(album_artist)

            # Add year and album using album-level earliest year
            album = metadata.get("album") or "Unknown-Album"
            key = (album_artist, album)
            year_val: int = album_earliest_year.get(key, 0)
            year_str = str(year_val).zfill(4)
            components.append(f"{year_str}_{album}")

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
        hierarchies = self._filters.get_hierarchies()
        if not hierarchies:
            logger.error("No hierarchies found")
            return paths

        # Get all values for each hierarchy.
        hierarchy_values: dict[int, list[FilterValueRecord]] = {}
        for hierarchy in hierarchies:
            values = self._filters.get_values(hierarchy.id)
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
        hierarchies: list[FilterHierarchyRecord],
        hierarchy_values: dict[int, list[FilterValueRecord]],
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

        # Build an O(1) lookup index for (hierarchy_id, file_hash) -> value
        # This avoids repeated linear scans per file per hierarchy.
        value_index: dict[tuple[int, str], str] = {}
        file_hashes: set[str] = set()
        for h_id, values in hierarchy_values.items():
            for v in values:
                file_hashes.add(v.file_hash)
                value_index[(h_id, v.file_hash)] = v.value

        # Group files by hierarchy values.
        for file_hash in file_hashes:
            group_key: list[str] = []
            missing = False
            for hierarchy in hierarchies:
                value = value_index.get((hierarchy.id, file_hash))
                if value is None:
                    logger.warning("Missing value for hierarchy %s, file %s", hierarchy.name, file_hash)
                    missing = True
                    break
                group_key.append(value)
            if not missing:
                key = tuple(group_key)
                groups.setdefault(key, set()).add(file_hash)

        return groups

    def _find_value_for_file(self, hierarchy_id: int, file_hash: str, values: list[FilterValueRecord]) -> str | None:  # pyright: ignore[reportUnusedFunction] - kept for external callers if any
        """(Deprecated) Linear search for a file's hierarchy value.

        Kept for compatibility with any external callers; internal code now
        uses an indexed lookup in ``_group_files_by_hierarchies`` for O(1) access.
        """
        for value in values:
            if value.hierarchy_id == hierarchy_id and value.file_hash == file_hash:
                return value.value
        return None

    def _generate_group_paths(
        self,
        hierarchies: list[FilterHierarchyRecord],
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

    def _assemble_relative_path(
        self,
        components: list[str],
        hierarchies: list[FilterHierarchyRecord] | None = None,
    ) -> Path:
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


@final
class _FilterDaoAdapter(FilterQueryPort):
    """Adapter that projects FilterDAO results onto port records."""

    def __init__(self, conn: Connection) -> None:
        self._dao = FilterDAO(conn)

    def get_hierarchies(self) -> list[FilterHierarchyRecord]:
        return [
            FilterHierarchyRecord(id=item.id, name=item.name, priority=item.priority)
            for item in self._dao.get_hierarchies()
        ]

    def get_values(self, hierarchy_id: int) -> list[FilterValueRecord]:
        return [
            FilterValueRecord(
                hierarchy_id=value.hierarchy_id,
                file_hash=value.file_hash,
                value=value.value,
            )
            for value in self._dao.get_values(hierarchy_id)
        ]
