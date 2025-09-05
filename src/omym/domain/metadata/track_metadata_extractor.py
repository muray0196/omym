"""Audio file metadata extraction functionality."""

import abc
from pathlib import Path
from typing import Any, ClassVar, cast, override, TYPE_CHECKING
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.id3 import ID3
from mutagen.oggopus import OggOpus
from mutagen.dsf import DSF
from mutagen._util import MutagenError
from omym.infra.logger.logger import logger
from omym.domain.metadata.track_metadata import TrackMetadata

if TYPE_CHECKING:
    from mutagen import MutagenTags, MutagenTagsBytes, TagValue, TagsDict
else:
    MutagenTags: type[object] = object
    MutagenTagsBytes: type[object] = object
    TagValue: type[object] = object
    TagsDict: type[dict[str, Any]] = dict


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
            str_key: str = key.decode(encoding="utf-8")
            str_value: str = value.decode(encoding="utf-8")
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
    parts: list[str] = value.split(sep="/") if value else []
    num: int | None = int(parts[0]) if parts and parts[0].isdigit() else None
    total: int | None = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    return num, total


def parse_tuple_numbers(data: list[tuple[int, int]] | None) -> tuple[int | None, int | None]:
    """Parse a list of numeric tuples and return the first tuple with zeros converted to None."""
    if data:
        first: tuple[int, int] = data[0]
        num: int | None = first[0] if first[0] != 0 else None
        total: int | None = first[1] if first[1] != 0 else None
        return num, total
    return None, None


def parse_year(date_str: str) -> int | None:
    """Parse a year from a string (expects the first 4 characters to be digits)."""
    return int(date_str[:4]) if date_str and len(date_str) >= 4 and date_str[:4].isdigit() else None


def safe_get_dsf(tags: TagsDict, key: str, default: str = "") -> str:
    """Safely get a DSF tag value from a dictionary."""
    try:
        value: TagValue = tags.get(key, default)
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
        value: str | list[str] | list[tuple[int, int]] | None = tags.get(key)
        if isinstance(value, list):
            return safe_get_first(data=cast(list[str], value), default=default or "")
        elif isinstance(value, str):
            return value
        return default


class BaseAudioExtractor(AudioFormatExtractor, abc.ABC):
    """Base class for audio metadata extractors."""

    # Format specific file class and initialization parameters
    FILE_CLASS: ClassVar[type | None] = None
    FILE_INIT_PARAMS: ClassVar[dict[str, Any]] = {}

    TAG_MAPPING: ClassVar[dict[str, str]] = {
        "title": "",
        "artist": "",
        "album_artist": "",
        "album": "",
        "track": "",
        "disc": "",
        "date": "",
    }

    def _open_file(self, file_path: Path) -> MutagenTags:
        """Open the audio file and get its tags.

        Args:
            file_path: Path to the audio file.

        Returns:
            MutagenTags: The audio file tags object.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            NotImplementedError: If FILE_CLASS is not defined in subclass.
            Exception: If file cannot be opened or tags cannot be read.
        """
        try:
            if self.FILE_CLASS is None:
                raise NotImplementedError("FILE_CLASS must be defined in subclass")

            file_instance = self.FILE_CLASS(file_path, **self.FILE_INIT_PARAMS)
            return cast(MutagenTags, file_instance)

        except MutagenError as e:
            logger.error(
                "Failed to extract %s metadata from %s: %s",
                self.__class__.__name__.replace("Extractor", ""),
                file_path,
                e,
            )
            if "No such file" in str(e):
                raise FileNotFoundError(str(e)) from e
            raise
        except Exception as e:
            logger.error(
                "Failed to extract %s metadata from %s: %s",
                self.__class__.__name__.replace("Extractor", ""),
                file_path,
                e,
            )
            raise

    @abc.abstractmethod
    def _get_tag_value(self, tags: Any, key: str) -> str | None:
        """Get a tag value from the audio file.

        Args:
            tags: The audio file tags object.
            key: The tag key to get.

        Returns:
            str | None: The tag value, or None if not found.
        """
        pass

    @override
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file.

        Returns:
            TrackMetadata: The extracted metadata.

        Raises:
            Exception: If metadata extraction fails.
        """
        try:
            tags: MutagenTags = self._open_file(file_path)
            logger.debug("Opened file %s with tags type: %s", file_path, type(tags))

            # Extract basic metadata
            title: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["title"])
            logger.debug("Title tag: %s", title)
            artist: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["artist"])
            logger.debug("Artist tag: %s", artist)
            album_artist: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["album_artist"])
            logger.debug("Album artist tag: %s", album_artist)
            album: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["album"])
            logger.debug("Album tag: %s", album)

            # Track information
            track_str: str = self._get_tag_value(tags, key=self.TAG_MAPPING["track"]) or ""
            logger.debug("Track tag: %s", track_str)
            track_number, track_total = parse_slash_separated(value=track_str)

            # Disc information
            disc_str: str = self._get_tag_value(tags, key=self.TAG_MAPPING["disc"]) or ""
            logger.debug("Disc tag: %s", disc_str)
            disc_number, disc_total = parse_slash_separated(value=disc_str)

            # Date information
            date_str: str = self._get_tag_value(tags, key=self.TAG_MAPPING["date"]) or ""
            logger.debug("Date tag: %s", date_str)
            year: int | None = parse_year(date_str)

            metadata: TrackMetadata = TrackMetadata(
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
            logger.debug("Extracted metadata: %s", metadata)
            return metadata

        except Exception as e:
            logger.error("Failed to extract metadata from %s: %s", file_path, e)
            raise


class Mp3Extractor(BaseAudioExtractor):
    """Extractor for MP3 files using EasyID3 tags."""

    FILE_CLASS: ClassVar[type | None] = MP3
    FILE_INIT_PARAMS: ClassVar[dict[str, Any]] = {"ID3": EasyID3}

    TAG_MAPPING: ClassVar[dict[str, str]] = {
        "title": "title",
        "artist": "artist",
        "album_artist": "albumartist",
        "album": "album",
        "track": "tracknumber",
        "disc": "discnumber",
        "date": "date",
    }

    def _get_tag_value(self, tags: MutagenTags, key: str) -> str | None:
        return BaseTagExtractor.get_str_tag(tags, key)


class FlacExtractor(BaseAudioExtractor):
    """Extractor for FLAC files."""

    FILE_CLASS: ClassVar[type | None] = FLAC
    FILE_INIT_PARAMS: ClassVar[dict[str, Any]] = {}

    TAG_MAPPING: ClassVar[dict[str, str]] = {
        "title": "title",
        "artist": "artist",
        "album_artist": "albumartist",
        "album": "album",
        "track": "tracknumber",
        "disc": "discnumber",
        "date": "date",
    }

    def _get_tag_value(self, tags: MutagenTags, key: str) -> str | None:
        return BaseTagExtractor.get_str_tag(tags, key)


class OpusExtractor(BaseAudioExtractor):
    """Extractor for Opus (.opus) files using Vorbis comments."""

    FILE_CLASS: ClassVar[type | None] = OggOpus
    FILE_INIT_PARAMS: ClassVar[dict[str, Any]] = {}

    # Opus (Ogg) uses Vorbis-style comment keys, matching FLAC
    TAG_MAPPING: ClassVar[dict[str, str]] = {
        "title": "title",
        "artist": "artist",
        "album_artist": "albumartist",
        "album": "album",
        "track": "tracknumber",
        "disc": "discnumber",
        "date": "date",
    }

    def _get_tag_value(self, tags: MutagenTags, key: str) -> str | None:
        return BaseTagExtractor.get_str_tag(tags, key)


class M4aExtractor(BaseAudioExtractor):
    """Extractor for M4A/AAC files using MP4 tags."""

    FILE_CLASS: ClassVar[type | None] = MP4
    FILE_INIT_PARAMS: ClassVar[dict[str, Any]] = {}

    TAG_MAPPING: ClassVar[dict[str, str]] = {
        "title": "\xa9nam",
        "artist": "\xa9ART",
        "album_artist": "aART",
        "album": "\xa9alb",
        "track": "trkn",
        "disc": "disk",
        "date": "\xa9day",
    }

    def _get_tag_value(self, tags: MutagenTags, key: str) -> str | None:
        if key in ["trkn", "disk"]:
            # Handle tuple values for track and disc numbers
            value: list[tuple[int, int]] | None = cast(list[tuple[int, int]] | None, tags.get(key))
            if not value:
                return None
            num, total = parse_tuple_numbers(data=value)
            return f"{num or ''}/{total or ''}"
        return BaseTagExtractor.get_str_tag(tags, key)


class DsfExtractor(BaseAudioExtractor):
    """Extractor for DSF files."""

    FILE_CLASS: ClassVar[type | None] = DSF
    FILE_INIT_PARAMS: ClassVar[dict[str, Any]] = {}

    TAG_MAPPING: ClassVar[dict[str, str]] = {
        "title": "TIT2",
        "artist": "TPE1",
        "album_artist": "TPE2",
        "album": "TALB",
        "track": "TRCK",
        "disc": "TPOS",
        "date": "TDRC",
    }

    def _get_tag_value(self, tags: ID3, key: str) -> str | None:
        try:
            frame: TagValue = cast(MutagenTags, tags).get(key)
            if frame is None:
                return None
            frame_obj: object = cast(object, frame)
            if hasattr(frame_obj, "text"):
                text: str | list[str] = cast(str | list[str], getattr(frame_obj, "text"))
                if isinstance(text, (list, tuple)) and text:
                    return str(text[0])
                return str(text)
            return None
        except Exception as e:
            logger.warning("Failed to get ID3 tag %r: %s", key, e)
            return None


class MetadataExtractor:
    """Facade class for extracting metadata from audio files.

    This class selects the appropriate extractor based on file extension.
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {".flac", ".mp3", ".m4a", ".dsf", ".opus"}

    # Mapping from file extension to corresponding extractor instance.
    _format_map: ClassVar[dict[str, AudioFormatExtractor]] = {
        ".mp3": Mp3Extractor(),
        ".flac": FlacExtractor(),
        ".m4a": M4aExtractor(),
        ".dsf": DsfExtractor(),
        ".opus": OpusExtractor(),
    }

    # Compatibility wrappers for tests and external patching
    @classmethod
    def _extract_mp3(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".mp3"].extract_metadata(file_path)

    @classmethod
    def _extract_flac(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".flac"].extract_metadata(file_path)

    @classmethod
    def _extract_m4a(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".m4a"].extract_metadata(file_path)

    @classmethod
    def _extract_dsf(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".dsf"].extract_metadata(file_path)

    @classmethod
    def _extract_opus(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".opus"].extract_metadata(file_path)

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
        ext: str = file_path.suffix.lower()
        if ext not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")

        # Route through per-format methods to allow easy mocking in tests
        method_map: dict[str, type[TrackMetadata] | callable[[Path], TrackMetadata]] = {
            ".mp3": cls._extract_mp3,
            ".flac": cls._extract_flac,
            ".m4a": cls._extract_m4a,
            ".dsf": cls._extract_dsf,
            ".opus": cls._extract_opus,
        }

        return method_map[ext](file_path)
