"""Shared base classes for metadata extractors.

Where: src/omym/features/metadata/usecases/extraction/_base_extractors.py
What: Define abstract base classes that encapsulate shared tag handling logic.
Why: Support the track metadata extractor refactor by decoupling reusable pieces into dedicated modules.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, ClassVar, TYPE_CHECKING, cast, override

from mutagen._util import MutagenError

from omym.platform.logging import logger

from ._tag_utils import parse_slash_separated, parse_year, safe_get_first
from ...domain.track_metadata import TrackMetadata

if TYPE_CHECKING:
    from mutagen import MutagenTags
else:  # pragma: no cover - typing convenience
    MutagenTags: type[object] = object

__all__ = [
    "AudioFormatExtractor",
    "BaseTagExtractor",
    "BaseAudioExtractor",
]


class AudioFormatExtractor(abc.ABC):
    """Abstract base class for audio metadata extractors."""

    @abc.abstractmethod
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file."""
        raise NotImplementedError


class BaseTagExtractor:
    """Provides common helper methods for tag extraction."""

    @staticmethod
    def get_str_tag(tags: MutagenTags, key: str, default: str | None = None) -> str | None:
        """Extract the first string value for a key from tag collection."""
        value: str | list[str] | list[tuple[int, int]] | None = tags.get(key)
        if isinstance(value, list):
            return safe_get_first(data=cast(list[str], value), default=default or "")
        if isinstance(value, str):
            return value
        return default


class BaseAudioExtractor(AudioFormatExtractor, abc.ABC):
    """Base class for audio metadata extractors."""

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
        """Open the audio file and get its tags."""
        try:
            if self.FILE_CLASS is None:
                raise NotImplementedError("FILE_CLASS must be defined in subclass")

            file_instance = self.FILE_CLASS(file_path, **self.FILE_INIT_PARAMS)
            return cast(MutagenTags, file_instance)
        except MutagenError as exc:
            logger.error(
                "Failed to extract %s metadata from %s: %s",
                self.__class__.__name__.replace("Extractor", ""),
                file_path,
                exc,
            )
            if "No such file" in str(exc):
                raise FileNotFoundError(str(exc)) from exc
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to extract %s metadata from %s: %s",
                self.__class__.__name__.replace("Extractor", ""),
                file_path,
                exc,
            )
            raise

    @abc.abstractmethod
    def _get_tag_value(self, tags: Any, key: str) -> str | None:
        """Get a tag value from the audio file."""
        raise NotImplementedError

    @override
    def extract_metadata(self, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file."""
        try:
            tags: MutagenTags = self._open_file(file_path)
            logger.debug("Opened file %s with tags type: %s", file_path, type(tags))

            title: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["title"])
            logger.debug("Title tag: %s", title)
            artist: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["artist"])
            logger.debug("Artist tag: %s", artist)
            album_artist: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["album_artist"])
            logger.debug("Album artist tag: %s", album_artist)
            album: str | None = self._get_tag_value(tags, key=self.TAG_MAPPING["album"])
            logger.debug("Album tag: %s", album)

            track_str: str = self._get_tag_value(tags, key=self.TAG_MAPPING["track"]) or ""
            logger.debug("Track tag: %s", track_str)
            track_number, track_total = parse_slash_separated(value=track_str)

            disc_str: str = self._get_tag_value(tags, key=self.TAG_MAPPING["disc"]) or ""
            logger.debug("Disc tag: %s", disc_str)
            disc_number, disc_total = parse_slash_separated(value=disc_str)

            year_str_preferred: str = self._get_tag_value(tags, key="year") or ""
            date_str: str = self._get_tag_value(tags, key=self.TAG_MAPPING["date"]) or ""
            logger.debug("Year tag: %s; Date tag: %s", year_str_preferred, date_str)
            year: int | None = parse_year(year_str_preferred) or parse_year(date_str)

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
        except Exception as exc:
            logger.error("Failed to extract metadata from %s: %s", file_path, exc)
            raise
