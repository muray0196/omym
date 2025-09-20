"""Music file grouping functionality."""

from pathlib import Path
from typing import ClassVar

from omym.domain.metadata.track_metadata_extractor import MetadataExtractor
from omym.infra.logger.logger import logger

from omym.domain.organization.path_format import parse_path_format

class MusicGrouper:
    """Group music files based on path format."""

    SUPPORTED_COMPONENTS: ClassVar[set[str]] = {"AlbumArtist", "Album", "Genre", "Year"}

    def group_by_path_format(self, files: list[Path], path_format: str) -> dict[str, dict[str, str | None]]:
        """Group files based on the specified path format.

        Args:
            files: List of file paths to process.
            path_format: Format string (e.g., "AlbumArtist/Album").

        Returns:
            dict[str, dict[str, str | None]]: Dictionary mapping file paths to metadata.
                The metadata dictionary contains optional string values for each metadata field.
        """
        result: dict[str, dict[str, str | None]] = {}
        components = parse_path_format(path_format)

        # Validate components
        invalid_components = [c for c in components if c not in self.SUPPORTED_COMPONENTS]
        if invalid_components:
            logger.error(
                "Unsupported path components: %s. Supported components are: %s",
                ", ".join(invalid_components),
                ", ".join(sorted(self.SUPPORTED_COMPONENTS)),
            )
            return result

        for file_path in files:
            try:
                # Extract metadata
                metadata = MetadataExtractor.extract(file_path)
                if not metadata:
                    logger.warning("Failed to extract metadata from %s", file_path)
                    continue

                # Convert metadata to dictionary
                metadata_dict: dict[str, str | None] = {
                    "title": metadata.title,
                    "artist": metadata.artist,
                    "album": metadata.album,
                    "album_artist": metadata.album_artist,
                    "genre": metadata.genre,
                    "year": str(metadata.year) if metadata.year else None,
                    "track_number": str(metadata.track_number) if metadata.track_number else None,
                    "track_total": str(metadata.track_total) if metadata.track_total else None,
                    "disc_number": str(metadata.disc_number) if metadata.disc_number else None,
                    "disc_total": str(metadata.disc_total) if metadata.disc_total else None,
                }

                # Check if all required components have values
                missing_components: list[str] = []
                for component in components:
                    value = self._get_component_value(component, metadata_dict)
                    if not value:
                        missing_components.append(component)

                if missing_components:
                    logger.warning(
                        "Missing required components for %s: %s",
                        file_path,
                        ", ".join(missing_components),
                    )
                    continue

                # Add to result
                result[str(file_path)] = metadata_dict

            except Exception as e:
                logger.error("Failed to process file %s: %s", file_path, e)

        return result

    def _get_component_value(self, component: str, metadata: dict[str, str | None]) -> str:
        """Get the value for a path component from metadata.

        Args:
            component: Component name (e.g., "AlbumArtist").
            metadata: File metadata dictionary with optional string values.

        Returns:
            str: Component value, empty string if not found.
        """
        if component == "AlbumArtist":
            # No fallback to track artist; require album_artist explicitly
            return metadata.get("album_artist") or ""
        elif component == "Album":
            return metadata.get("album") or ""
        elif component == "Genre":
            return metadata.get("genre") or ""
        elif component == "Year":
            return metadata.get("year") or ""
        else:
            logger.warning("Unknown path component: %s", component)
            return ""
