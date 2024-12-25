"""Audio file metadata extraction functionality."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, ClassVar, Dict, List, Union, Tuple, Any, cast

from mutagen.id3 import ID3
from mutagen._file import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from omym.utils.logger import logger
from omym.core.metadata import TrackMetadata


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
    def _extract_mp3(file_path: Path) -> TrackMetadata:
        """Extract metadata from MP3 file.

        Args:
            file_path: Path to the MP3 file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            Exception: If metadata extraction fails.
        """
        try:
            audio = cast(EasyID3, MP3(file_path, ID3=EasyID3))

            # Extract track and disc numbers
            track_str = MetadataExtractor._safe_get_first(audio.get("tracknumber"))
            track = track_str.split("/") if track_str else [""]
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = (
                int(track[1]) if len(track) > 1 and track[1].isdigit() else None
            )

            disc_str = MetadataExtractor._safe_get_first(audio.get("discnumber"))
            disc = disc_str.split("/") if disc_str else [""]
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = MetadataExtractor._safe_get_first(audio.get("date"))
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._safe_get_first(audio.get("title")) or None,
                artist=MetadataExtractor._safe_get_first(audio.get("artist")) or None,
                album_artist=MetadataExtractor._safe_get_first(audio.get("albumartist"))
                or None,
                album=MetadataExtractor._safe_get_first(audio.get("album")) or None,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=file_path.suffix.lower(),
            )
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
            audio = cast(FLAC, FLAC(file_path))

            # Extract track and disc numbers
            track_str = MetadataExtractor._safe_get_first(audio.get("tracknumber"))
            track = track_str.split("/") if track_str else [""]
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = (
                int(track[1]) if len(track) > 1 and track[1].isdigit() else None
            )

            disc_str = MetadataExtractor._safe_get_first(audio.get("discnumber"))
            disc = disc_str.split("/") if disc_str else [""]
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = MetadataExtractor._safe_get_first(audio.get("date"))
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._safe_get_first(audio.get("title")) or None,
                artist=MetadataExtractor._safe_get_first(audio.get("artist")) or None,
                album_artist=MetadataExtractor._safe_get_first(audio.get("albumartist"))
                or None,
                album=MetadataExtractor._safe_get_first(audio.get("album")) or None,
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
            audio = cast(MP4, MP4(file_path))

            # Extract track and disc numbers
            track = MetadataExtractor._safe_get_tuple(audio.get("trkn"))
            track_number = track[0] if track[0] != 0 else None
            track_total = track[1] if track[1] != 0 else None

            disc = MetadataExtractor._safe_get_tuple(audio.get("disk"))
            disc_number = disc[0] if disc[0] != 0 else None
            disc_total = disc[1] if disc[1] != 0 else None

            # Extract year
            year_str = MetadataExtractor._safe_get_first(audio.get("\xa9day"))
            year = int(year_str) if year_str and year_str.isdigit() else None

            return TrackMetadata(
                title=MetadataExtractor._safe_get_first(audio.get("\xa9nam")) or None,
                artist=MetadataExtractor._safe_get_first(audio.get("\xa9ART")) or None,
                album_artist=MetadataExtractor._safe_get_first(audio.get("aART"))
                or None,
                album=MetadataExtractor._safe_get_first(audio.get("\xa9alb")) or None,
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
            audio: Any = MutagenFile(file_path)
            if not audio or not audio.tags:
                return TrackMetadata(file_extension=file_path.suffix.lower())

            tags = audio.tags

            # Extract track and disc numbers
            track_str = str(tags.get("TRCK", ""))
            track = track_str.split("/") if track_str else [""]
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = (
                int(track[1]) if len(track) > 1 and track[1].isdigit() else None
            )

            disc_str = str(tags.get("TPOS", ""))
            disc = disc_str.split("/") if disc_str else [""]
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = str(tags.get("TDRC", ""))
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=str(tags.get("TIT2", None)) or None,
                artist=str(tags.get("TPE1", None)) or None,
                album_artist=str(tags.get("TPE2", None)) or None,
                album=str(tags.get("TALB", None)) or None,
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
            ValueError: If the file format is not supported.
            Exception: If metadata extraction fails.
        """
        # Check file format first
        suffix = file_path.suffix.lower()
        if suffix not in cls.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {suffix}. "
                f"Supported formats are: {', '.join(cls.SUPPORTED_FORMATS)}"
            )

        # Then check file existence
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.debug("Extracting metadata from %s", file_path)

        try:
            if suffix == ".mp3":
                return cls._extract_mp3(file_path)
            elif suffix == ".flac":
                return cls._extract_flac(file_path)
            elif suffix == ".m4a":
                return cls._extract_m4a(file_path)
            elif suffix == ".dsf":
                return cls._extract_dsf(file_path)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
        except Exception as e:
            logger.error("Metadata extraction failed for %s: %s", file_path, e)
            raise
