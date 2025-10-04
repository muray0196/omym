"""Summary: MusicBrainz romanization adapter bridging the platform client.
Why: Provide a port implementation that wires cache configuration and fetch helpers."""

from __future__ import annotations

from omym.features.metadata.usecases.ports import ArtistCachePort, RomanizationPort
from omym.platform.musicbrainz.client import (
    configure_romanization_cache,
    fetch_romanized_name,
)
from omym.platform.musicbrainz.cache import save_cached_name


class MusicBrainzRomanizationAdapter(RomanizationPort):
    """Delegate romanization operations to the MusicBrainz platform helpers."""

    def configure_cache(self, cache: ArtistCachePort | None) -> None:
        configure_romanization_cache(cache)

    def fetch_romanized_name(self, artist_name: str) -> str | None:
        return fetch_romanized_name(artist_name)

    def save_cached_name(
        self,
        original: str,
        romanized: str,
        *,
        source: str | None = None,
    ) -> None:
        save_cached_name(original, romanized, source=source)


__all__ = ["MusicBrainzRomanizationAdapter"]
