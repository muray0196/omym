"""Filtering engine for organizing music files."""

from sqlite3 import Connection
from typing import final

from omym.platform.db.daos.albums_dao import AlbumDAO
from omym.platform.db.daos.filter_dao import FilterDAO

from ..domain.path_format import parse_path_format

@final
class HierarchicalFilter:
    """Filter engine for organizing music files."""

    conn: Connection
    filter_dao: FilterDAO
    album_dao: AlbumDAO

    def __init__(self, conn: Connection):
        """Initialize filter engine.

        Args:
            conn: SQLite database connection.
        """
        self.conn = conn
        self.filter_dao = FilterDAO(conn)
        self.album_dao = AlbumDAO(conn)

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
            if not self.filter_dao.insert_hierarchy(name, i):
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
        hierarchies = self.filter_dao.get_hierarchies()

        for hierarchy in hierarchies:
            value = metadata.get(hierarchy.name.lower())
            if not value:
                warnings.append(f"Missing value for hierarchy '{hierarchy.name}' in file {file_hash}")
                continue

            if not self.filter_dao.insert_value(hierarchy.id, file_hash, value):
                warnings.append(f"Failed to register value for hierarchy '{hierarchy.name}' in file {file_hash}")

        return warnings
