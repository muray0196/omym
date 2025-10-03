"""File name generation helpers.

Where: features/path/usecases/renamer/filename.py
What: Build canonical track file names using cached artist IDs and album context.
Why: Allow reuse across use cases without depending on full processor orchestration.
"""

from __future__ import annotations

from typing import ClassVar, final

from omym.shared.track_metadata import TrackMetadata
from omym.features.path.domain.sanitizer import Sanitizer
from omym.platform.logging import logger

from .cached_artist_id import CachedArtistIdGenerator


@final
class FileNameGenerator:
    """Generate file names from track metadata."""

    artist_id_generator: CachedArtistIdGenerator
    _album_track_widths: ClassVar[dict[str, int]] = {}
    _albums_requiring_disc_prefix: ClassVar[set[str]] = set()

    @classmethod
    def _get_album_key(cls, album_artist: str, album: str) -> str:
        aa = Sanitizer.sanitize_artist_name(album_artist)
        al = Sanitizer.sanitize_album_name(album)
        return f"{aa}|{al}"

    @classmethod
    def register_album_track_width(cls, metadata: TrackMetadata) -> None:
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
        self.artist_id_generator = artist_id_generator

    def generate(self, metadata: TrackMetadata) -> str:
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

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to generate file name: %s", exc)
            return f"ERROR_{metadata.file_extension}"


__all__ = ["FileNameGenerator"]
