"""Filtering engine for organizing music files."""

from typing import List, Dict, Optional, Tuple

from omym.utils.logger import logger
from omym.db.dao_albums import AlbumDAO, AlbumInfo, TrackPosition
from omym.db.dao_filter import FilterDAO, FilterHierarchy, FilterValue


class HierarchicalFilter:
    """Filter engine for organizing music files."""

    def __init__(self, conn):
        """Initialize filter engine.

        Args:
            conn: Database connection.
        """
        self.conn = conn
        self.filter_dao = FilterDAO(conn)
        self.album_dao = AlbumDAO(conn)

    def register_hierarchies(self, path_format: str) -> List[str]:
        """Register filter hierarchies from path format.

        Args:
            path_format: Path format string (e.g., "AlbumArtist/Album").

        Returns:
            List[str]: List of warnings.
        """
        warnings = []
        components = [c.strip() for c in path_format.split("/") if c.strip()]

        for i, name in enumerate(components):
            if not self.filter_dao.insert_hierarchy(name, i):
                warnings.append(f"Failed to register hierarchy: {name}")

        return warnings

    def process_file(self, file_hash: str, metadata: dict) -> List[str]:
        """Process a file and register its filter values.

        Args:
            file_hash: Hash of the file content.
            metadata: File metadata.

        Returns:
            List[str]: List of warnings.
        """
        warnings = []
        hierarchies = self.filter_dao.get_hierarchies()

        for hierarchy in hierarchies:
            value = metadata.get(hierarchy.name.lower())
            if not value:
                warnings.append(
                    f"Missing value for hierarchy '{hierarchy.name}' in file {file_hash}"
                )
                continue

            if not self.filter_dao.insert_value(hierarchy.id, file_hash, value):
                warnings.append(
                    f"Failed to register value for hierarchy '{hierarchy.name}' "
                    f"in file {file_hash}"
                )

        return warnings

    def _get_hierarchy_value(
        self, name: str, metadata: Dict[str, str]
    ) -> Optional[str]:
        """Get value for a hierarchy from metadata.

        Args:
            name: Hierarchy name.
            metadata: File metadata.

        Returns:
            Optional[str]: Hierarchy value if found.
        """
        if name == "AlbumArtist":
            return metadata.get("album_artist")
        elif name == "Album":
            return metadata.get("album")
        elif name == "Genre":
            return metadata.get("genre")
        else:
            logger.warning("Unknown hierarchy: %s", name)
            return None
