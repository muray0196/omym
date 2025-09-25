"""Filtering engine use cases.

Where: features/organization/usecases.
What: Manage hierarchy registration and per-file filter values via injected ports.
Why: Keep database specifics outside the use case for easier testing and adapter swaps.
"""

from sqlite3 import Connection
from typing import final

from omym.platform.db.daos.filter_dao import FilterDAO

from ..domain.path_format import parse_path_format
from .ports import FilterHierarchyRecord, FilterRegistryPort

@final
class HierarchicalFilter:
    """Filter engine for organizing music files."""

    _filters: FilterRegistryPort

    def __init__(
        self,
        conn: Connection | None = None,
        *,
        filter_port: FilterRegistryPort | None = None,
    ) -> None:
        """Initialize filter engine.

        Args:
            conn: Legacy SQLite connection used when ``filter_port`` is omitted.
            filter_port: Port implementation providing hierarchy persistence.
        """
        if filter_port is not None:
            self._filters = filter_port
        elif conn is not None:
            self._filters = _FilterDaoAdapter(conn)
        else:
            raise ValueError("HierarchicalFilter requires filter_port or conn")

    def register_hierarchies(self, path_format: str) -> list[str]:
        """Register filter hierarchies from path format.

        Args:
            path_format: Path format string (e.g., "AlbumArtist/Album").
                Each component in the path represents a hierarchy level.

        Returns:
            list[str]: List of warning messages if any registration failed.
        """
        warnings: list[str] = []
        components = parse_path_format(path_format)

        for i, name in enumerate(components):
            if not self._filters.insert_hierarchy(name, i):
                warnings.append(f"Failed to register hierarchy: {name}")

        return warnings

    def process_file(self, file_hash: str, metadata: dict[str, str | None]) -> list[str]:
        """Process a file and register its filter values.

        Args:
            file_hash: Hash of the file content.
            metadata: File metadata dictionary with optional string values.

        Returns:
            list[str]: List of warning messages if any processing failed.
        """
        warnings: list[str] = []
        hierarchies = self._filters.get_hierarchies()

        for hierarchy in hierarchies:
            value = metadata.get(hierarchy.name.lower())
            if not value:
                warnings.append(f"Missing value for hierarchy '{hierarchy.name}' in file {file_hash}")
                continue

            if not self._filters.insert_value(hierarchy.id, file_hash, value):
                warnings.append(f"Failed to register value for hierarchy '{hierarchy.name}' in file {file_hash}")

        return warnings


@final
class _FilterDaoAdapter(FilterRegistryPort):
    """Adapter projecting FilterDAO into the filter registry port."""

    def __init__(self, conn: Connection) -> None:
        self._dao = FilterDAO(conn)

    def insert_hierarchy(self, name: str, priority: int) -> int | None:
        return self._dao.insert_hierarchy(name, priority)

    def get_hierarchies(self) -> list[FilterHierarchyRecord]:
        return [
            FilterHierarchyRecord(id=item.id, name=item.name, priority=item.priority)
            for item in self._dao.get_hierarchies()
        ]

    def insert_value(self, hierarchy_id: int, file_hash: str, value: str) -> bool:
        return self._dao.insert_value(hierarchy_id, file_hash, value)
