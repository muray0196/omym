"""
Summary: Filtering engine use cases relying on injected ports only.
Why: Enforce hexagonal boundaries by removing direct DAO construction in the use case.
"""

from typing import final

from ..domain.path_format import parse_path_format
from .ports import FilterRegistryPort

@final
class HierarchicalFilter:
    """Filter engine for organizing music files."""

    _filters: FilterRegistryPort

    def __init__(self, filter_port: FilterRegistryPort) -> None:
        """Initialize filter engine with a persistence port.

        Args:
            filter_port: Port implementation providing hierarchy persistence.
        """
        self._filters = filter_port

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


