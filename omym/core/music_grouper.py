"""Music file grouping functionality."""

from pathlib import Path
from typing import Dict, List, Optional

from omym.core.metadata import TrackMetadata
from omym.core.metadata_extractor import MetadataExtractor
from omym.utils.logger import logger


class MusicGrouper:
    """Group music files based on path format."""

    def __init__(self):
        """Initialize the grouper."""
        pass

    def group_by_path_format(
        self, files: List[Path], path_format: str
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """Group files based on the specified path format.

        Args:
            files: List of file paths to process.
            path_format: Format string (e.g., "AlbumArtist/Album").

        Returns:
            Dict[str, Dict[str, Optional[str]]]: Dictionary mapping file paths to metadata.
                The metadata dictionary contains optional string values for each metadata field.
        """
        result: Dict[str, Dict[str, Optional[str]]] = {}
        components = [c.strip() for c in path_format.split("/") if c.strip()]

        for file_path in files:
            try:
                # Extract metadata
                metadata = MetadataExtractor.extract(file_path)
                if not metadata:
                    logger.warning(f"Failed to extract metadata from {file_path}")
                    continue

                # Convert metadata to dictionary
                metadata_dict: Dict[str, Optional[str]] = {
                    "title": metadata.title,
                    "artist": metadata.artist,
                    "album": metadata.album,
                    "album_artist": metadata.album_artist,
                    "genre": metadata.genre,
                    "year": str(metadata.year) if metadata.year else None,
                    "track_number": str(metadata.track_number)
                    if metadata.track_number
                    else None,
                    "track_total": str(metadata.track_total)
                    if metadata.track_total
                    else None,
                    "disc_number": str(metadata.disc_number)
                    if metadata.disc_number
                    else None,
                    "disc_total": str(metadata.disc_total)
                    if metadata.disc_total
                    else None,
                }

                # Check if all required components have values
                missing_components = []
                for component in components:
                    value = self._get_component_value(component, metadata_dict)
                    if not value:
                        missing_components.append(component)

                if missing_components:
                    logger.warning(
                        f"Missing required components for {file_path}: {', '.join(missing_components)}"
                    )
                    continue

                # Add to result
                result[str(file_path)] = metadata_dict

            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")

        return result

    def _get_component_value(
        self, component: str, metadata: Dict[str, Optional[str]]
    ) -> str:
        """Get the value for a path component from metadata.

        Args:
            component: Component name (e.g., "AlbumArtist").
            metadata: File metadata dictionary with optional string values.

        Returns:
            str: Component value, empty string if not found.
        """
        if component == "AlbumArtist":
            return metadata.get("album_artist") or metadata.get("artist") or ""
        elif component == "Album":
            return metadata.get("album") or ""
        elif component == "Genre":
            return metadata.get("genre") or ""
        else:
            logger.warning(f"Unknown path component: {component}")
            return ""
