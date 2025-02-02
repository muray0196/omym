"""Audio file metadata extraction functionality."""

import abc
from pathlib import Path
from typing import ClassVar, cast, override, TypeVar, Protocol

from mutagen._file import File as MutagenFile  # pyright: ignore[reportUnknownVariableType]
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen._util import MutagenError

from omym.utils.logger import logger
from omym.core.metadata.track_metadata import TrackMetadata


# Type definitions for mutagen tags
T = TypeVar("T")
TagValue = str | list[str] | list[tuple[int, int]] | None
TagsDict = dict[str, TagValue]


class MutagenTags(Protocol):
    """Protocol for mutagen tags."""

    def get(self, key: str, default: T | None = None) -> TagValue | T: ...
    def items(self) -> list[tuple[str, TagValue]]: ...


class MutagenTagsBytes(Protocol):
    """Protocol for mutagen tags that use bytes."""

    def get(self, key: bytes, default: T | None = None) -> bytes | T: ...
    def items(self) -> list[tuple[bytes, bytes]]: ...


def convert_bytes_tags(tags: MutagenTagsBytes) -> TagsDict:
    """Convert byte tags to string tags.

    Args:
        tags: Tags with byte keys and values.

    Returns:
        Dictionary with string keys and values.
    """
    result: TagsDict = {}
    for key, value in tags.items():
        try:
            str_key = key.decode("utf-8")
            str_value = value.decode("utf-8")
            result[str_key] = str_value
        except (UnicodeDecodeError, AttributeError):
            continue
    return result


def safe_get_first(data: list[str] | None, default: str = "") -> str:
    """Safely get the first element from a list or return the default."""
    return data[0] if data else default


def parse_slash_separated(value: str) -> tuple[int | None, int | None]:
    """Parse a string in 'number/total' format.

    Returns a tuple (number, total) or (None, None) if conversion fails.
    """
    parts = value.split("/") if value else []
    num = int(parts[0]) if parts and parts[0].isdigit() else None
    total = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    return num, total


def parse_tuple_numbers(data: list[tuple[int, int]] | None) -> tuple[int | None, int | None]:
    """Parse a list of numeric tuples and return the first tuple with zeros converted to None."""
    if data:
        first = data[0]
        num = first[0] if first[0] != 0 else None
        total = first[1] if first[1] != 0 else None
        return num, total
    return None, None


def parse_year(date_str: str) -> int | None:
    """Parse a year from a string (expects the first 4 characters to be digits)."""
    return int(date_str[:4]) if date_str and len(date_str) >= 4 and date_str[:4].isdigit() else None


def safe_get_dsf(tags: TagsDict, key: str, default: str = "") -> str:
    """Safely get a DSF tag value from a dictionary."""
    try:
        value = tags.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


class AudioFormatExtractor(abc.ABC):
    """Abstract base class for audio metadata extractors."""

    @abc.abstractmethod
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            Exception: When extraction fails.
        """
        pass


class BaseTagExtractor:
    """Provides common helper methods for tag extraction."""

    @staticmethod
    def get_str_tag(tags: MutagenTags, key: str, default: str | None = None) -> str | None:
        """Extract the first string value for a key from tag collection."""
        value = tags.get(key)
        if isinstance(value, list):
            return safe_get_first(cast(list[str], value), default or "")
        elif isinstance(value, str):
            return value
        return default


class Mp3Extractor(AudioFormatExtractor):
    """Extractor for MP3 files using EasyID3 tags."""

    @override
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        try:
            audio = cast(MutagenTags, MP3(file_path, ID3=EasyID3))
        except MutagenError as e:
            logger.error("Failed to extract MP3 metadata from %s: %s", file_path, e)
            if "No such file" in str(e):
                raise FileNotFoundError(str(e)) from e
            raise

        title = BaseTagExtractor.get_str_tag(audio, "title")
        artist = BaseTagExtractor.get_str_tag(audio, "artist")
        album_artist = BaseTagExtractor.get_str_tag(audio, "albumartist")
        album = BaseTagExtractor.get_str_tag(audio, "album")

        track_str = safe_get_first(cast(list[str], audio.get("tracknumber")), "")
        track_number, track_total = parse_slash_separated(track_str)

        disc_str = safe_get_first(cast(list[str], audio.get("discnumber")), "")
        disc_number, disc_total = parse_slash_separated(disc_str)

        date_str = safe_get_first(cast(list[str], audio.get("date")), "")
        year = parse_year(date_str)

        return TrackMetadata(
            title=title,
            artist=artist,
            album_artist=album_artist,
            album=album,
            track_number=track_number,
            track_total=track_total,
            disc_number=disc_number,
            disc_total=disc_total,
            year=year,
            file_extension=file_path.suffix.lower(),
        )


class FlacExtractor(AudioFormatExtractor):
    """Extractor for FLAC files."""

    @override
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        try:
            audio = cast(MutagenTags, FLAC(file_path))
        except Exception as e:
            logger.error("Failed to extract FLAC metadata from %s: %s", file_path, e)
            raise

        title = BaseTagExtractor.get_str_tag(audio, "title")
        artist = BaseTagExtractor.get_str_tag(audio, "artist")
        album_artist = BaseTagExtractor.get_str_tag(audio, "albumartist")
        album = BaseTagExtractor.get_str_tag(audio, "album")

        track_str = safe_get_first(cast(list[str], audio.get("tracknumber")), "")
        track_number, track_total = parse_slash_separated(track_str)

        disc_str = safe_get_first(cast(list[str], audio.get("discnumber")), "")
        disc_number, disc_total = parse_slash_separated(disc_str)

        date_str = safe_get_first(cast(list[str], audio.get("date")), "")
        year = parse_year(date_str)

        return TrackMetadata(
            title=title,
            artist=artist,
            album_artist=album_artist,
            album=album,
            track_number=track_number,
            track_total=track_total,
            disc_number=disc_number,
            disc_total=disc_total,
            year=year,
            file_extension=file_path.suffix.lower(),
        )


class M4aExtractor(AudioFormatExtractor):
    """Extractor for M4A/AAC files using MP4 tags."""

    @override
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        try:
            audio = cast(MutagenTags, MP4(file_path))
        except Exception as e:
            logger.error("Failed to extract M4A metadata from %s: %s", file_path, e)
            raise

        # In MP4, standard tag keys are slightly different.
        title = BaseTagExtractor.get_str_tag(audio, "\xa9nam")
        artist = BaseTagExtractor.get_str_tag(audio, "\xa9ART")
        album_artist = BaseTagExtractor.get_str_tag(audio, "aART")
        album = BaseTagExtractor.get_str_tag(audio, "\xa9alb")

        # For track and disk, MP4 stores a list of tuples.
        track_tuple = cast(list[tuple[int, int]], audio.get("trkn"))
        track_number, track_total = parse_tuple_numbers(track_tuple)

        disc_tuple = cast(list[tuple[int, int]], audio.get("disk"))
        disc_number, disc_total = parse_tuple_numbers(disc_tuple)

        date_str = BaseTagExtractor.get_str_tag(audio, "\xa9day", "")
        year = int(date_str) if date_str and date_str.isdigit() else None

        return TrackMetadata(
            title=title,
            artist=artist,
            album_artist=album_artist,
            album=album,
            track_number=track_number,
            track_total=track_total,
            disc_number=disc_number,
            disc_total=disc_total,
            year=year,
            file_extension=file_path.suffix.lower(),
        )


class DsfExtractor(AudioFormatExtractor):
    """Extractor for DSF files which use ID3-like tags."""

    @override
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        try:
            audio = MutagenFile(file_path)
            if not audio or not hasattr(audio, "tags") or audio.tags is None:  # pyright: ignore[reportUnknownMemberType]
                return TrackMetadata(file_extension=file_path.suffix.lower())
            tags = convert_bytes_tags(cast(MutagenTagsBytes, audio.tags))
        except Exception as e:
            logger.error("Failed to open DSF file %s: %s", file_path, e)
            raise

        title = safe_get_dsf(tags, "TIT2") or None
        artist = safe_get_dsf(tags, "TPE1") or None
        album_artist = safe_get_dsf(tags, "TPE2") or None
        album = safe_get_dsf(tags, "TALB") or None

        track_str = safe_get_dsf(tags, "TRCK", "")
        track_number, track_total = parse_slash_separated(track_str)

        disc_str = safe_get_dsf(tags, "TPOS", "")
        disc_number, disc_total = parse_slash_separated(disc_str)

        date_str = safe_get_dsf(tags, "TDRC", "")
        year = parse_year(date_str)

        return TrackMetadata(
            title=title,
            artist=artist,
            album_artist=album_artist,
            album=album,
            track_number=track_number,
            track_total=track_total,
            disc_number=disc_number,
            disc_total=disc_total,
            year=year,
            file_extension=file_path.suffix.lower(),
        )


class MetadataExtractor:
    """Facade class for extracting metadata from audio files.

    This class selects the appropriate extractor based on file extension.
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {".flac", ".mp3", ".m4a", ".dsf"}

    # Mapping from file extension to corresponding extractor instance.
    _format_map: ClassVar[dict[str, AudioFormatExtractor]] = {
        ".mp3": Mp3Extractor(),
        ".flac": FlacExtractor(),
        ".m4a": M4aExtractor(),
        ".dsf": DsfExtractor(),
    }

    @classmethod
    def extract(cls, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            ValueError: If the file format is unsupported.
            Exception: If extraction fails.
        """
        ext = file_path.suffix.lower()
        if ext not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")

        extractor = cls._format_map[ext]
        return extractor.extract_metadata(file_path)
