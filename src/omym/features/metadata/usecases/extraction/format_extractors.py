"""Format-specific metadata extractors.

Where: src/omym/features/metadata/usecases/extraction/format_extractors.py
What: Define concrete metadata extractors for supported audio formats.
Why: Separate format logic from the facade to simplify future maintenance and extensions.
"""

from __future__ import annotations

from typing import Any, ClassVar, TYPE_CHECKING, cast

from mutagen.dsf import DSF
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus

from omym.platform.logging import logger

from ._base_extractors import BaseAudioExtractor, BaseTagExtractor
from ._tag_utils import parse_tuple_numbers

if TYPE_CHECKING:
    from mutagen import MutagenTags, TagValue
else:  # pragma: no cover - typing convenience
    MutagenTags: type[object] = object
    TagValue: type[object] = object

__all__ = [
    "Mp3Extractor",
    "FlacExtractor",
    "OpusExtractor",
    "M4aExtractor",
    "DsfExtractor",
]


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
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to get ID3 tag %r: %s", key, exc)
            return None
