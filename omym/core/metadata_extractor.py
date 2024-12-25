"""Audio file metadata extraction functionality."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from omym.utils.logger import logger
from omym.core.metadata import TrackMetadata


class MetadataExtractor:
    """Extract metadata from audio files."""

    SUPPORTED_FORMATS = {".flac", ".mp3", ".m4a", ".dsf"}

    @staticmethod
    def _extract_mp3(file_path: Path) -> TrackMetadata:
        """Extract metadata from MP3 file."""
        try:
            audio = MP3(file_path, ID3=EasyID3)

            # Extract track and disc numbers
            track = audio.get("tracknumber", [""])[0].split("/")
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = (
                int(track[1]) if len(track) > 1 and track[1].isdigit() else None
            )

            disc = audio.get("discnumber", [""])[0].split("/")
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = audio.get("date", [""])[0]
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=audio.get("title", [None])[0],
                artist=audio.get("artist", [None])[0],
                album_artist=audio.get("albumartist", [None])[0],
                album=audio.get("album", [None])[0],
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
        """Extract metadata from FLAC file."""
        try:
            audio = FLAC(file_path)

            # Extract track and disc numbers
            track = audio.get("tracknumber", [""])[0].split("/")
            track_number = int(track[0]) if track and track[0].isdigit() else None
            track_total = (
                int(track[1]) if len(track) > 1 and track[1].isdigit() else None
            )

            disc = audio.get("discnumber", [""])[0].split("/")
            disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
            disc_total = int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None

            # Extract year
            date = audio.get("date", [""])[0]
            year = int(date[:4]) if date and date[:4].isdigit() else None

            return TrackMetadata(
                title=audio.get("title", [None])[0],
                artist=audio.get("artist", [None])[0],
                album_artist=audio.get("albumartist", [None])[0],
                album=audio.get("album", [None])[0],
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
        """Extract metadata from M4A/AAC file."""
        try:
            audio = MP4(file_path)

            # Extract track and disc numbers
            track = audio.get("trkn", [(None, None)])[0]
            track_number = track[0] if track[0] is not None and track[0] != 0 else None
            track_total = track[1] if track[1] is not None and track[1] != 0 else None

            disc = audio.get("disk", [(None, None)])[0]
            disc_number = disc[0] if disc[0] is not None and disc[0] != 0 else None
            disc_total = disc[1] if disc[1] is not None and disc[1] != 0 else None

            return TrackMetadata(
                title=audio.get("\xa9nam", [None])[0],
                artist=audio.get("\xa9ART", [None])[0],
                album_artist=audio.get("aART", [None])[0],
                album=audio.get("\xa9alb", [None])[0],
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=audio.get("\xa9day", [None])[0],
                file_extension=file_path.suffix.lower(),
            )
        except Exception as e:
            logger.error("Failed to extract M4A metadata from %s: %s", file_path, e)
            raise

    @staticmethod
    def _extract_dsf(file_path: Path) -> TrackMetadata:
        """Extract metadata from DSF file."""
        try:
            # DSF files use ID3 tags like MP3
            audio = File(file_path)
            if audio.tags:
                tags = audio.tags

                # Extract track and disc numbers
                track = str(tags.get("TRCK", "")).split("/")
                track_number = int(track[0]) if track and track[0].isdigit() else None
                track_total = (
                    int(track[1]) if len(track) > 1 and track[1].isdigit() else None
                )

                disc = str(tags.get("TPOS", "")).split("/")
                disc_number = int(disc[0]) if disc and disc[0].isdigit() else None
                disc_total = (
                    int(disc[1]) if len(disc) > 1 and disc[1].isdigit() else None
                )

                # Extract year
                date = str(tags.get("TDRC", ""))
                year = int(date[:4]) if date and date[:4].isdigit() else None

                return TrackMetadata(
                    title=str(tags.get("TIT2", None)),
                    artist=str(tags.get("TPE1", None)),
                    album_artist=str(tags.get("TPE2", None)),
                    album=str(tags.get("TALB", None)),
                    track_number=track_number,
                    track_total=track_total,
                    disc_number=disc_number,
                    disc_total=disc_total,
                    year=year,
                    file_extension=file_path.suffix.lower(),
                )

            return TrackMetadata(file_extension=file_path.suffix.lower())

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
