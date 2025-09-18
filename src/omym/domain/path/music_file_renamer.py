"""Renaming logic functionality."""

import re
from typing import ClassVar, Protocol, final, runtime_checkable
from pathlib import Path
from unidecode import unidecode
import pykakasi
import langid
from omym.domain.path.sanitizer import Sanitizer
from omym.domain.metadata.track_metadata import TrackMetadata
from omym.infra.logger.logger import logger


@runtime_checkable
class ArtistCacheWriter(Protocol):
    """Protocol for artist cache interactions used by ID generation."""

    def get_artist_id(self, artist_name: str) -> str | None:
        """Return a cached artist ID if present."""

        ...

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        """Persist a generated artist ID; returns True on success."""

        ...


@final
class ArtistIdGenerator:
    """Generate artist IDs."""

    # Characters to keep in the ID (alphanumeric and hyphens)
    KEEP_CHARS: ClassVar[re.Pattern[str]] = re.compile(r"[^A-Z0-9-]")

    # Vowels to remove (except for the first character of each word)
    VOWELS: ClassVar[re.Pattern[str]] = re.compile(r"[AEIOU]")

    # ID length
    ID_LENGTH: ClassVar[int] = 5

    # Default ID for when generation fails
    DEFAULT_ID: ClassVar[str] = "NOART"

    # Initialize pykakasi converter
    _kakasi: ClassVar = pykakasi.Kakasi()

    @classmethod
    def _process_word(cls, word: str) -> tuple[str, str]:
        """Process a single word by keeping its first character and removing vowels from the rest.

        Args:
            word: A word to process.

        Returns:
            tuple[str, str]: A tuple containing:
                - The processed word with vowels removed except for the first character
                - The original word (for fallback if the processed word is too short)
        """
        if not word:
            return "", ""

        # Keep the first character as is
        first_char = word[0]

        # Remove vowels from the rest of the word, but keep the first vowel if it's the first character
        if len(word) > 1:
            rest = word[1:]
            rest = cls.VOWELS.sub("", rest)
            processed = first_char + rest
        else:
            processed = first_char

        return processed, word

    @classmethod
    def _transliterate_japanese(cls, text: str) -> str:
        """Transliterate Japanese text to Latin script using pykakasi.

        Args:
            text: Japanese text to transliterate.

        Returns:
            str: Transliterated text in uppercase Latin characters.
        """
        try:
            # Convert to romaji and uppercase
            result = cls._kakasi.convert(text)
            return "".join(item["hepburn"] for item in result).upper()
        except Exception as e:
            logger.warning("Japanese transliteration failed for '%s': %s", text, e)
            return text

    @classmethod
    def generate(cls, artist_name: str | None) -> str:
        """Generate an artist ID (up to 5 characters) from an artist name.

        The generation process:
        1. If the artist name is empty or None, return "NOART"
        2. Convert to Latin characters:
           - For English text: Use unidecode for normalization
           - For Japanese text: Use pykakasi for transliteration
           - For other languages: Use unidecode as fallback
        3. Sanitize and convert to uppercase
        4. If no alphanumeric characters remain, return "XXXXX"
        5. Process each word:
           - Keep the first character of each word
           - Remove vowels from the rest of each word
        6. If the result is less than 5 chars, use original words
        7. Take first 5 chars; do not pad if shorter

        Args:
            artist_name: The artist name to generate an ID for.

        Returns:
            str: An artist ID up to 5 characters, either:
                - A generated ID based on the artist name
                - "NOART" if the input is empty/None
                - "XXXXX" if no valid characters remain after processing
        """
        try:
            # Return DEFAULT_ID if artist_name is empty or None
            if not artist_name or not artist_name.strip():
                return cls.DEFAULT_ID

            # Split multi-artist strings separated by comma-space and combine
            if ", " in artist_name:
                parts = [part.strip() for part in artist_name.split(", ") if part.strip()]
                if parts:
                    artist_name = "".join(parts)

            # First, try to detect language and transliterate if needed
            name = artist_name
            try:
                # Detect language using langid
                lang, _ = langid.classify(name)
                # Treat Chinese as Japanese since langid often detects Japanese kanji as Chinese
                if lang in ["ja", "zh"]:
                    # Use pykakasi for Japanese text
                    name = cls._transliterate_japanese(name)
                else:
                    # Use unidecode for all other languages
                    name = unidecode(name)
            except Exception as e:
                logger.warning(
                    "Language detection/transliteration failed for '%s': %s",
                    artist_name,
                    e,
                )
                # Continue with the original name but still try to normalize it
                name = unidecode(artist_name)

            # Sanitize and convert to uppercase
            name = Sanitizer.sanitize_artist_name(name).upper()
            if not name:
                return "XXXXX"

            # Split into words and process each word
            words = name.split("-")
            processed_results: list[tuple[str, str]] = [cls._process_word(word) for word in words]

            # Try with vowels removed
            processed_words = [result[0] for result in processed_results]
            processed_id = "".join(processed_words)

            # If the processed ID is too short, use original words
            if len(processed_id) < cls.ID_LENGTH:
                original_words = [result[1] for result in processed_results]
                name = "".join(original_words)
            else:
                name = processed_id

            # Take first 5 characters; do not pad if shorter
            if len(name) > cls.ID_LENGTH:
                return name[: cls.ID_LENGTH]
            else:
                return name

        except Exception as e:
            logger.error("Failed to generate artist ID for '%s': %s", artist_name, e)
            return cls.DEFAULT_ID


@final
class CachedArtistIdGenerator:
    """Generate and cache artist IDs."""

    dao: ArtistCacheWriter

    def __init__(self, dao: ArtistCacheWriter):
        """Initialize generator with a DAO.

        Args:
            dao: Artist cache interface for database access.
        """
        self.dao = dao

    def generate(self, artist_name: str | None) -> str:
        """Generate or retrieve a cached artist ID.

        This method first checks the cache for an existing ID.
        If not found, it generates a new ID and caches it.
        If an error occurs during generation, returns the default ID without caching.

        Args:
            artist_name: The artist name to generate an ID for.

        Returns:
            str: An artist ID up to 5 characters, either:
                - A cached ID if found in the database
                - A newly generated ID if not found in cache
                - "NOART" if the input is empty/None or an error occurs
        """
        try:
            # Return DEFAULT_ID if artist_name is empty or None
            if not artist_name or not artist_name.strip():
                return ArtistIdGenerator.DEFAULT_ID

            # Normalize artist name
            normalized_name = artist_name.strip()

            # Check cache first
            cached_id = self.dao.get_artist_id(normalized_name)
            if cached_id:
                if self._is_valid_id(cached_id):
                    return cached_id
                else:
                    # If cached ID is invalid, remove it and generate new one
                    logger.warning(
                        "Found invalid cached ID '%s' for artist '%s', regenerating",
                        cached_id,
                        normalized_name,
                    )

            # Generate new ID
            new_id = ArtistIdGenerator.generate(normalized_name)

            # Validate generated ID
            if not self._is_valid_id(new_id):
                logger.error(
                    "Generated invalid ID '%s' for artist '%s'",
                    new_id,
                    normalized_name,
                )
                return ArtistIdGenerator.DEFAULT_ID

            # Cache the new ID only if it's a valid, successfully generated ID
            # (not DEFAULT_ID, XXXXX, or any other special case)
            if (
                new_id not in [ArtistIdGenerator.DEFAULT_ID, "XXXXX"]
                and self._is_valid_id(new_id)
                and all(c.isalnum() or c == "-" for c in new_id)
            ):
                retry_count = 3
                while retry_count > 0:
                    try:
                        if self.dao.insert_artist_id(normalized_name, new_id):
                            logger.debug(
                                "Successfully cached artist ID '%s' for '%s'",
                                new_id,
                                normalized_name,
                            )
                            break
                    except Exception as e:
                        logger.warning(
                            "Failed to cache artist ID for '%s' (attempt %d): %s",
                            normalized_name,
                            4 - retry_count,
                            e,
                        )
                    retry_count -= 1
                    if retry_count > 0:
                        import time

                        time.sleep(0.1)  # Short delay before retry
            else:
                logger.debug(
                    "Skipping cache for invalid/special artist ID '%s' for '%s'",
                    new_id,
                    normalized_name,
                )

            return new_id

        except Exception as e:
            logger.error(
                "Failed to generate/cache artist ID for '%s': %s",
                artist_name,
                e,
            )
            return ArtistIdGenerator.DEFAULT_ID

    @staticmethod
    def _is_valid_id(artist_id: str) -> bool:
        """Check if an artist ID is valid.

        Args:
            artist_id: The artist ID to validate.

        Returns:
            bool: True if the ID is valid, False otherwise.
        """
        if not artist_id:
            return False

        # Allow IDs of length 1..ID_LENGTH
        if len(artist_id) > ArtistIdGenerator.ID_LENGTH:
            return False

        if artist_id in [ArtistIdGenerator.DEFAULT_ID, "XXXXX"]:
            return True

        # Check if ID contains only allowed characters
        return bool(ArtistIdGenerator.KEEP_CHARS.sub("", artist_id) == artist_id)


@final
class FileNameGenerator:
    """Generate file names from track metadata."""

    artist_id_generator: CachedArtistIdGenerator
    # Cache for per-album track number width (minimum 2)
    _album_track_widths: ClassVar[dict[str, int]] = {}
    # Cache of albums that require disc prefixes in file names
    _albums_requiring_disc_prefix: ClassVar[set[str]] = set()

    @classmethod
    def _get_album_key(cls, album_artist: str, album: str) -> str:
        """Generate a unique key for an album for width lookup.

        Uses sanitized names to align with directory generation.

        Args:
            album_artist: Album artist name.
            album: Album name.

        Returns:
            str: Unique key for the album.
        """
        aa = Sanitizer.sanitize_artist_name(album_artist)
        al = Sanitizer.sanitize_album_name(album)
        return f"{aa}|{al}"

    @classmethod
    def register_album_track_width(cls, metadata: TrackMetadata) -> None:
        """Register album-level caches derived from a track's metadata.

        This populates the track-number padding width and notes whether the
        album requires disc prefixes in generated file names. Tracks missing a
        usable number are ignored for padding purposes.

        Args:
            metadata: Track metadata containing album and track information.
        """
        album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"
        album = metadata.album if metadata.album else "Unknown-Album"
        key = cls._get_album_key(album_artist, album)

        disc_number = metadata.disc_number
        disc_total = metadata.disc_total
        if (
            isinstance(disc_total, int) and disc_total > 1
        ) or (
            isinstance(disc_number, int) and disc_number > 1
        ):
            cls._albums_requiring_disc_prefix.add(key)

        width = 0
        if isinstance(metadata.track_number, int) and metadata.track_number > 0:
            width = len(str(metadata.track_number))
        if width <= 0:
            return
        width = max(2, width)

        current = cls._album_track_widths.get(key)
        if current is None or width > current:
            cls._album_track_widths[key] = width

    @classmethod
    def _should_include_disc_prefix(cls, key: str, metadata: TrackMetadata) -> bool:
        """Determine whether a disc prefix is required for the album.

        Args:
            key: Album cache key built from album artist and title.
            metadata: Track metadata for the file being processed.

        Returns:
            bool: True when the generated file name should include the disc prefix.
        """
        disc_number = metadata.disc_number
        if not isinstance(disc_number, int) or disc_number <= 0:
            return False

        disc_total = metadata.disc_total
        if isinstance(disc_total, int) and disc_total > 1:
            return True

        if disc_number > 1:
            return True

        return key in cls._albums_requiring_disc_prefix

    def __init__(self, artist_id_generator: CachedArtistIdGenerator):
        """Initialize generator.

        Args:
            artist_id_generator: Generator for artist IDs.
        """
        self.artist_id_generator = artist_id_generator

    def generate(self, metadata: TrackMetadata) -> str:
        """Generate a file name from track metadata.

        Format:
            - Multi-disc albums: D{disc_number}_{track_number}_{title}_{artist_id}.{extension}
            - Single-disc albums: {track_number}_{title}_{artist_id}.{extension}

        Args:
            metadata: Track metadata to generate file name from.

        Returns:
            str: Generated file name with the appropriate format and extension.
                If any required fields are missing, they will be replaced with
                placeholder values (e.g., "XX" for missing track numbers).
        """
        try:
            artist_id = self.artist_id_generator.generate(metadata.artist)

            title = Sanitizer.sanitize_title(metadata.title)

            album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"
            album = metadata.album if metadata.album else "Unknown-Album"
            key = self._get_album_key(album_artist, album)
            width = max(2, self._album_track_widths.get(key, 2))
            track_num = (
                str(metadata.track_number).zfill(width)
                if isinstance(metadata.track_number, int) and metadata.track_number > 0
                else "XX"
            )

            include_disc_prefix = self._should_include_disc_prefix(key, metadata)
            prefix = f"D{metadata.disc_number}" if include_disc_prefix else ""

            extension = metadata.file_extension or ""

            if prefix:
                return f"{prefix}_{track_num}_{title}_{artist_id}{extension}"
            return f"{track_num}_{title}_{artist_id}{extension}"

        except Exception as e:
            logger.error("Failed to generate file name: %s", e)
            return f"ERROR_{metadata.file_extension}"


@final
class DirectoryGenerator:
    """Generate directory structure from track metadata."""

    # Cache for album years: dict[album_key, set[year]]
    _album_years: ClassVar[dict[str, set[int]]] = {}

    @classmethod
    def _get_album_key(cls, album_artist: str, album: str) -> str:
        """Generate a unique key for an album.

        Args:
            album_artist: Album artist name.
            album: Album name.

        Returns:
            str: Unique key for the album.
        """
        return f"{album_artist}|{album}"

    @classmethod
    def register_album_year(cls, metadata: TrackMetadata) -> None:
        """Register an album's year for later use.

        Args:
            metadata: Track metadata containing album information.
        """
        # Get album artist strictly from album_artist (no fallback to artist)
        album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"

        # Get album name
        album = metadata.album if metadata.album else "Unknown-Album"

        # Sanitize names
        album_artist = Sanitizer.sanitize_artist_name(album_artist)
        album = Sanitizer.sanitize_album_name(album)

        # Generate key
        key = cls._get_album_key(album_artist, album)

        # Get year (0 if missing)
        year = metadata.year if metadata.year else 0

        # Update years dictionary
        if key not in cls._album_years:
            cls._album_years[key] = {year}
        else:
            cls._album_years[key].add(year)

    @classmethod
    def get_album_year(cls, album_artist: str, album: str) -> int:
        """Get the year for an album.

        Use the earliest year from all tracks in the album.
        If no valid year is found, use 0000.

        Args:
            album_artist: Album artist name.
            album: Album name.

        Returns:
            int: Year to use for the album directory.
        """
        key = cls._get_album_key(album_artist, album)
        years = cls._album_years.get(key, {0})

        # Use the earliest year (excluding 0) per new spec
        non_zero_years: set[int] = {y for y in years if y != 0}
        if non_zero_years:
            return min(non_zero_years)
        return 0

    @classmethod
    def generate(cls, metadata: TrackMetadata) -> Path:
        """Generate a directory path from track metadata.

        Format:
        {album_artist}/{year}_{album}

        Args:
            metadata: Track metadata to generate directory path from.

        Returns:
            Path: Generated directory path.
        """
        try:
            # Get album artist strictly from album_artist (no fallback to artist)
            album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"

            # Sanitize album artist name
            album_artist = Sanitizer.sanitize_artist_name(album_artist)

            # Get album name (Unknown Album if missing)
            album = metadata.album if metadata.album else "Unknown-Album"
            # Sanitize album name
            album = Sanitizer.sanitize_album_name(album)

            # Register this album's year
            cls.register_album_year(metadata)

            # Get year based on all tracks in the album
            year = cls.get_album_year(album_artist, album)
            year_str = str(year).zfill(4)

            # Combine into path
            return Path(f"{album_artist}/{year_str}_{album}")

        except Exception as e:
            logger.error("Failed to generate directory path: %s", e)
            # Return a safe default path in case of error
            return Path("ERROR/0000_ERROR")
