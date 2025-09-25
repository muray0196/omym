"""Directory generation helpers.

Where: features/path/usecases/renamer/directory.py
What: Build album directory paths using sanitized metadata and year aggregation.
Why: Keep album-level state isolated from higher-level orchestration.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, final

from omym.features.metadata.domain.track_metadata import TrackMetadata
from omym.features.path.domain.sanitizer import Sanitizer
from omym.platform.logging import logger


@final
class DirectoryGenerator:
    """Generate directory structure from track metadata."""

    _album_years: ClassVar[dict[str, set[int]]] = {}

    @classmethod
    def _get_album_key(cls, album_artist: str, album: str) -> str:
        return f"{album_artist}|{album}"

    @classmethod
    def register_album_year(cls, metadata: TrackMetadata) -> None:
        album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"
        album = metadata.album if metadata.album else "Unknown-Album"

        album_artist = Sanitizer.sanitize_artist_name(album_artist)
        album = Sanitizer.sanitize_album_name(album)

        key = cls._get_album_key(album_artist, album)

        year = metadata.year if metadata.year else 0

        if key not in cls._album_years:
            cls._album_years[key] = {year}
        else:
            cls._album_years[key].add(year)

    @classmethod
    def get_album_year(cls, album_artist: str, album: str) -> int:
        key = cls._get_album_key(album_artist, album)
        years = cls._album_years.get(key, {0})

        non_zero_years: set[int] = {year for year in years if year != 0}
        if non_zero_years:
            return min(non_zero_years)
        return 0

    @classmethod
    def generate(cls, metadata: TrackMetadata) -> Path:
        try:
            album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"
            album_artist = Sanitizer.sanitize_artist_name(album_artist)

            album = metadata.album if metadata.album else "Unknown-Album"
            album = Sanitizer.sanitize_album_name(album)

            cls.register_album_year(metadata)

            year = cls.get_album_year(album_artist, album)
            year_str = str(year).zfill(4)

            return Path(f"{album_artist}/{year_str}_{album}")

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to generate directory path: %s", exc)
            return Path("ERROR/0000_ERROR")


__all__ = ["DirectoryGenerator"]
