"""Artist romanization helpers using MusicBrainz."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from omym.config.settings import USE_MB_ROMANIZATION
from omym.infra.logger.logger import logger
from omym.infra.musicbrainz.client import fetch_romanized_name
from omym.domain.metadata.track_metadata import TrackMetadata

ArtistFetcher = Callable[[str], str | None]


def _default_enabled() -> bool:
    """Return whether MusicBrainz romanization is enabled via settings."""
    return USE_MB_ROMANIZATION


def _default_fetcher(name: str) -> str | None:
    """Default fetcher delegating to the MusicBrainz client helper."""
    return fetch_romanized_name(name)


@dataclass(slots=True)
class ArtistRomanizer:
    """Romanize artist names using MusicBrainz WS2.

    The class memoizes lookups within its lifecycle to avoid duplicated
    network calls and obey MusicBrainz rate limiting etiquette enforced by
    the shared client module.
    """

    enabled_supplier: Callable[[], bool] = field(default=_default_enabled)
    fetcher: ArtistFetcher = field(default=_default_fetcher)
    _cache: dict[str, str] = field(default_factory=dict, init=False)

    def romanize_name(self, name: str | None) -> str | None:
        """Return a romanized version of an artist name when available.

        Args:
            name: Raw artist name extracted from metadata.

        Returns:
            Romanized artist name if MusicBrainz returns one; otherwise the
            original name (including whitespace-only inputs).
        """
        if name is None:
            return None
        trimmed = name.strip()
        if not trimmed:
            return name
        if not self.enabled_supplier():
            return name
        if trimmed.isascii():
            return name
        cached = self._cache.get(trimmed)
        if cached is not None:
            return cached
        try:
            romanized = self.fetcher(trimmed)
        except Exception as exc:  # pragma: no cover - defensive logging only
            logger.warning("Failed to romanize artist '%s': %s", trimmed, exc)
            romanized = None
        normalized = romanized.strip() if romanized else None
        if normalized:
            self._cache[trimmed] = normalized
            return normalized
        self._cache[trimmed] = name
        return name

    def romanize_metadata(self, metadata: TrackMetadata | None) -> TrackMetadata | None:
        """Apply romanization to artist-related fields within metadata.

        Args:
            metadata: Mutable track metadata structure to update.

        Returns:
            The same metadata instance with artist fields optionally
            romanized. ``None`` is returned if ``metadata`` is ``None``.
        """
        if metadata is None:
            return None
        metadata.artist = self.romanize_name(metadata.artist)
        metadata.album_artist = self.romanize_name(metadata.album_artist)
        return metadata
