"""File and path name sanitization functionality."""

import re
from pathlib import Path
from typing import final, ClassVar
import unicodedata

from omym.platform.logging.logger import logger


@final
class Sanitizer:
    """Sanitize file and path names."""

    # Characters to be replaced with hyphens (all non-word characters except hyphens)
    REPLACE_WITH_HYPHEN: ClassVar[re.Pattern[str]] = re.compile(r"[^\w-]")

    # Apostrophes to remove
    REMOVE_APOSTROPHE: ClassVar[re.Pattern[str]] = re.compile(r"'")

    # Multiple consecutive hyphens
    MULTIPLE_HYPHENS: ClassVar[re.Pattern[str]] = re.compile(r"-+")

    # Maximum lengths (in bytes)
    MAX_ARTIST_LENGTH: ClassVar[int] = 50
    MAX_ALBUM_LENGTH: ClassVar[int] = 90
    MAX_TRACK_LENGTH: ClassVar[int] = 90

    @classmethod
    def _clean_string(cls, text: str) -> str:
        """Clean a string by removing symbols and special characters.

        Args:
            text: Text to clean.

        Returns:
            str: Cleaned text with:
                - Normalized Unicode characters (NFKC)
                - Removed apostrophes
                - Special characters replaced with hyphens
                - Multiple hyphens compressed to single hyphens
                - No leading or trailing hyphens
        """
        # Normalize using NFKC
        text = unicodedata.normalize("NFKC", text)

        # Remove apostrophes
        text = cls.REMOVE_APOSTROPHE.sub("", text)

        # Replace prohibited characters (including spaces) with hyphens
        text = cls.REPLACE_WITH_HYPHEN.sub("-", text)

        # Compress multiple consecutive hyphens into one
        text = cls.MULTIPLE_HYPHENS.sub("-", text)

        # Remove hyphens at the start and end
        text = text.strip("-")

        return text

    @classmethod
    def sanitize_string(
        cls,
        text: str | int | float | None,
        max_length: int | None = None,
        preserve_extension: bool = False,
    ) -> str:
        """Sanitize a string by applying the following rules:
        1. Normalize using NFKC
        2. Remove apostrophes
        3. Replace prohibited characters with hyphens
        4. Compress multiple consecutive hyphens into one
        5. Remove hyphens at the start and end
        6. Truncate to max_length bytes if specified

        Args:
            text: String or number to sanitize.
            max_length: Maximum length in bytes, if None no length limit is applied.
            preserve_extension: Whether to preserve the file extension if present.

        Returns:
            str: Sanitized string that is:
                - Safe for use in file and path names
                - Within the specified byte length limit if provided
                - Has preserved file extension if requested and present
                - Empty string if input is None or contains only special characters

        Raises:
            Exception: If string sanitization fails for any reason.
        """
        if not text:
            return ""

        try:
            # Convert to string if not already
            text = str(text)

            # Split extension if needed
            extension = ""
            if preserve_extension and "." in text:
                base, extension = text.rsplit(".", 1)
                if extension and extension.isalnum():
                    text = base
                    extension = "." + extension
                else:
                    extension = ""

            # Clean the string
            text = cls._clean_string(text)

            # Handle edge cases: if the string is empty or only contained special characters
            if not text or text.isspace():
                return ""

            # Truncate if necessary
            if max_length and len((text + extension).encode("utf-8")) > max_length:
                while len((text + extension).encode("utf-8")) > max_length:
                    text = text[:-1]
                # Remove any trailing hyphens after truncation
                text = text.rstrip("-")

            return text + extension

        except Exception as e:
            logger.error("Failed to sanitize string '%s': %s", text, e)
            raise

    @classmethod
    def sanitize_artist_name(cls, artist_name: str | None) -> str:
        """Sanitize an artist name.

        Args:
            artist_name: Artist name to sanitize.

        Returns:
            str: Sanitized artist name that is:
                - Safe for use in file and path names
                - Within the MAX_ARTIST_LENGTH byte limit
                - Empty string if input is None or contains only special characters
        """
        return cls.sanitize_string(artist_name, cls.MAX_ARTIST_LENGTH)

    @classmethod
    def sanitize_album_name(cls, album_name: str | None) -> str:
        """Sanitize an album name.

        Args:
            album_name: Album name to sanitize.

        Returns:
            str: Sanitized album name that is:
                - Safe for use in file and path names
                - Within the MAX_ALBUM_LENGTH byte limit
                - Empty string if input is None or contains only special characters
        """
        return cls.sanitize_string(album_name, cls.MAX_ALBUM_LENGTH)

    @classmethod
    def sanitize_track_name(cls, track_name: str | None) -> str:
        """Sanitize a track name.

        Args:
            track_name: Track name to sanitize.

        Returns:
            str: Sanitized track name that is:
                - Safe for use in file and path names
                - Within the MAX_TRACK_LENGTH byte limit
                - 'Unknown-Title' if input is None or contains only special characters
        """
        sanitized = cls.sanitize_string(track_name, cls.MAX_TRACK_LENGTH)
        return sanitized if sanitized else "Unknown-Title"

    @classmethod
    def sanitize_path(cls, path: Path) -> Path:
        """Sanitize all components of a path.

        Args:
            path: Path to sanitize.

        Returns:
            Path: Sanitized path where:
                - Each component is safe for use in file and path names
                - Drive and root are preserved for absolute paths
                - Empty components are removed
                - File extension is preserved for the last component

        Raises:
            Exception: If path sanitization fails for any reason.
        """
        try:
            parts = list(path.parts)
            sanitized_parts: list[str] = []

            # Handle absolute paths
            if path.is_absolute():
                # Keep the root (and drive on Windows)
                if path.drive:
                    sanitized_parts.append(path.drive)
                sanitized_parts.append(path.root)
                parts = parts[1:]  # Skip the root for processing
                if parts and not parts[0].strip():  # Skip empty parts after root
                    parts = parts[1:]

            # Process remaining parts
            for i, part in enumerate(parts):
                # Preserve extension only for the last component (if it's a file)
                preserve_extension = i == len(parts) - 1
                sanitized = cls.sanitize_string(part, preserve_extension=preserve_extension)
                if sanitized:  # Only add non-empty parts
                    sanitized_parts.append(sanitized)

            # Reconstruct the path
            result = Path(sanitized_parts[0])
            for part in sanitized_parts[1:]:
                result = result / part

            return result

        except Exception as e:
            logger.error("Failed to sanitize path '%s': %s", path, e)
            raise

    @classmethod
    def sanitize_title(cls, title: str | None) -> str:
        """Sanitize a track title.

        Args:
            title: The track title to sanitize.

        Returns:
            str: Sanitized track title that is:
                - Safe for use in file and path names
                - 'Unknown-Title' if input is None or contains only special characters
        """
        if not title:
            return "Unknown-Title"

        # Use the standard sanitization process
        sanitized = cls.sanitize_string(title)
        return sanitized if sanitized else "Unknown-Title"
