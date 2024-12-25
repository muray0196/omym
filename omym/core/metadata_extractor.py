"""Audio file metadata extraction functionality."""

from pathlib import Path
from typing import (
    Optional,
    Set,
    ClassVar,
    Dict,
    List,
    Tuple,
    cast,
    Callable,
    Any,
)

from mutagen._file import File as MutagenFile  # type: ignore
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen._util import MutagenError

from omym.utils.logger import logger
from omym.core.metadata import TrackMetadata
from omym.core.mutagen_types import MutagenTags, MutagenFile as MutagenFileProtocol


class MetadataExtractor:
    """Extract metadata from audio files."""

    SUPPORTED_FORMATS: ClassVar[Set[str]] = {".flac", ".mp3", ".m4a", ".dsf"}

    @staticmethod
    def _safe_get_first(data: Optional[List[str]], default: str = "") -> str:
        """Safely get first item from list or return default.

        Args:
            data: List of strings or None
            default: Default value if list is None or empty

        Returns:
            str: First item or default value
        """
        if not data:
            return default
        return data[0]

    @staticmethod
    def _safe_get_tuple(
        data: Optional[List[Tuple[int, int]]], default: Tuple[int, int] = (0, 0)
    ) -> Tuple[int, int]:
        """Safely get first tuple from list or return default.

        Args:
            data: List of tuples or None
            default: Default value if list is None or empty

        Returns:
            Tuple[int, int]: First tuple or default value
        """
        if not data:
            return default
        return data[0]

    @staticmethod
    def _safe_get_tag_value(
        tags: MutagenTags, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Safely get tag value from audio tags.

        Args:
            tags: Audio file tags
            key: Tag key
            default: Default value if tag is not found

        Returns:
            Optional[str]: Tag value or default
        """
        try:
            value = str(tags.get(key, default))
            return value if value != str(default) else default
        except (AttributeError, TypeError, ValueError):
            return default

    @staticmethod
    def _get_audio_tag_value(audio: MutagenTags, key: str) -> Optional[List[str]]:
        """Get audio tag value with proper type casting.

        Args:
            audio: Audio file object
            key: Tag key

        Returns:
            Optional[List[str]]: Tag value or None
        """
        try:
            value = audio.get(key)
            return cast(Optional[List[str]], value)
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _get_audio_tuple_value(audio: MutagenTags, key: str) -> Optional[List[Tuple[int, int]]]:
        """Get audio tuple value with proper type casting.

        Args:
            audio: Audio file object
            key: Tag key

        Returns:
            Optional[List[Tuple[int, int]]]: Tag value or None
        """
        try:
            value = audio.get(key)
            return cast(Optional[List[Tuple[int, int]]], value)
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _get_dsf_tag_value(tags: Dict[str, Any], key: str, default: str = "") -> str:
        """Get DSF tag value with proper type casting.

        Args:
            tags: DSF file tags
            key: Tag key
            default: Default value if tag is not found

        Returns:
            str: Tag value or default
        """
        try:
            value = tags.get(key)
            if value is None:
                return default
            return str(value)
        except (AttributeError, TypeError, ValueError):
            return default

    @staticmethod
    def _extract_mp3(file_path: Path) -> TrackMetadata:
        """Extract metadata from MP3 file.

        Args:
            file_path: Path to the MP3 file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: If metadata extraction fails.
        """
        try:
            audio = cast(MutagenTags, MP3(file_path, ID3=EasyID3))  # type: ignore

            # Extract track and disc numbers
            track_str = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "tracknumber")
            )
            track = track_str.split("/") if track_str else [""]
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = int(track[1]) if len(track) > 1 and track[1].isdigit() else None

            disc_str = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "discnumber")
            )
            disc = disc_str.split("/") if disc_str else [""]
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "date")
            )
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "title")
                )
                or None,
                artist=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "artist")
                )
                or None,
                album_artist=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "albumartist")
                )
                or None,
                album=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "album")
                )
                or None,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=file_path.suffix.lower(),
            )
        except MutagenError as e:
            logger.error("Failed to extract MP3 metadata from %s: %s", file_path, e)
            if "No such file" in str(e):
                raise FileNotFoundError(str(e)) from e
            raise
        except Exception as e:
            logger.error("Failed to extract MP3 metadata from %s: %s", file_path, e)
            raise

    @staticmethod
    def _extract_flac(file_path: Path) -> TrackMetadata:
        """Extract metadata from FLAC file.

        Args:
            file_path: Path to the FLAC file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            Exception: If metadata extraction fails.
        """
        try:
            audio = cast(MutagenTags, FLAC(file_path))  # type: ignore

            # Extract track and disc numbers
            track_str = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "tracknumber")
            )
            track = track_str.split("/") if track_str else [""]
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = int(track[1]) if len(track) > 1 and track[1].isdigit() else None

            disc_str = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "discnumber")
            )
            disc = disc_str.split("/") if disc_str else [""]
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "date")
            )
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "title")
                )
                or None,
                artist=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "artist")
                )
                or None,
                album_artist=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "albumartist")
                )
                or None,
                album=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "album")
                )
                or None,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=file_path.suffix.lower(),
            )
        except Exception as e:
            logger.error("Failed to extract FLAC metadata from %s: %s", file_path, e)
            raise

    @staticmethod
    def _extract_m4a(file_path: Path) -> TrackMetadata:
        """Extract metadata from M4A/AAC file.

        Args:
            file_path: Path to the M4A file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            Exception: If metadata extraction fails.
        """
        try:
            audio = cast(MutagenTags, MP4(file_path))  # type: ignore

            # Extract track and disc numbers
            track = MetadataExtractor._safe_get_tuple(
                MetadataExtractor._get_audio_tuple_value(audio, "trkn")
            )
            track_number = track[0] if track[0] != 0 else None
            track_total = track[1] if track[1] != 0 else None

            disc = MetadataExtractor._safe_get_tuple(
                MetadataExtractor._get_audio_tuple_value(audio, "disk")
            )
            disc_number = disc[0] if disc[0] != 0 else None
            disc_total = disc[1] if disc[1] != 0 else None

            # Extract year
            year_str = MetadataExtractor._safe_get_first(
                MetadataExtractor._get_audio_tag_value(audio, "\xa9day")
            )
            year = int(year_str) if year_str and year_str.isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "\xa9nam")
                )
                or None,
                artist=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "\xa9ART")
                )
                or None,
                album_artist=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "aART")
                )
                or None,
                album=MetadataExtractor._safe_get_first(
                    MetadataExtractor._get_audio_tag_value(audio, "\xa9alb")
                )
                or None,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=file_path.suffix.lower(),
            )
        except Exception as e:
            logger.error("Failed to extract M4A metadata from %s: %s", file_path, e)
            raise

    @staticmethod
    def _extract_dsf(file_path: Path) -> TrackMetadata:
        """Extract metadata from DSF file.

        Args:
            file_path: Path to the DSF file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            Exception: If metadata extraction fails.
        """
        try:
            # DSF files use ID3 tags like MP3
            audio = cast(MutagenFileProtocol, MutagenFile(file_path))  # type: ignore
            if not audio or not audio.tags:
                return TrackMetadata(file_extension=file_path.suffix.lower())

            # We know audio.tags exists at this point and it's a dict-like object
            # Use MutagenTags protocol to handle the dynamic nature of mutagen tags
            tags = audio.tags  # type: ignore

            # Create a dictionary to handle the tags in a type-safe way
            tag_dict: Dict[str, Any] = {}
            for key, value in tags.items():
                tag_dict[key] = value

            # Extract track and disc numbers
            track_str = MetadataExtractor._get_dsf_tag_value(tag_dict, "TRCK", "")
            track = track_str.split("/") if track_str else [""]
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = int(track[1]) if len(track) > 1 and track[1].isdigit() else None

            disc_str = MetadataExtractor._get_dsf_tag_value(tag_dict, "TPOS", "")
            disc = disc_str.split("/") if disc_str else [""]
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = MetadataExtractor._get_dsf_tag_value(tag_dict, "TDRC", "")
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._get_dsf_tag_value(tag_dict, "TIT2") or None,
                artist=MetadataExtractor._get_dsf_tag_value(tag_dict, "TPE1") or None,
                album_artist=MetadataExtractor._get_dsf_tag_value(tag_dict, "TPE2") or None,
                album=MetadataExtractor._get_dsf_tag_value(tag_dict, "TALB") or None,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=file_path.suffix.lower(),
            )
        except Exception as e:
            logger.error("Failed to extract DSF metadata from %s: %s", file_path, e)
            raise

    @classmethod
    def extract(cls, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            ValueError: If file format is not supported.
            Exception: If metadata extraction fails.
        """
        if file_path.suffix.lower() not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        format_map: Dict[str, Callable[[Path], TrackMetadata]] = {
            ".mp3": cls._extract_mp3,
            ".flac": cls._extract_flac,
            ".m4a": cls._extract_m4a,
            ".dsf": cls._extract_dsf,
        }

        return format_map[file_path.suffix.lower()](file_path)
