"""Where: src/omym/platform/musicbrainz/cache.py
What: Lightweight indirection for artist romanization cache integration.
Why: Allow the MusicBrainz client to run without hard dependency on a cache.
"""

from __future__ import annotations

from typing import Protocol

from omym.platform.logging import logger


class RomanizationCache(Protocol):
    """A minimal cache protocol used by the MusicBrainz client."""

    def get_romanized_name(self, artist_name: str) -> str | None:
        ...

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        *,
        source: str | None = None,
    ) -> bool:
        ...


_cache: RomanizationCache | None = None


def configure_cache(cache: RomanizationCache | None) -> None:
    """Attach the cache implementation consumed by the HTTP client layer."""

    global _cache
    _cache = cache


def read_cached_name(artist_name: str) -> str | None:
    """Best-effort cache lookup with defensive logging."""

    if _cache is None:
        return None
    try:
        return _cache.get_romanized_name(artist_name)
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.warning("Failed to read romanization cache for '%s': %s", artist_name, exc)
        return None


def save_cached_name(original: str, romanized: str, *, source: str | None = None) -> None:
    """Persist a romanized name when a cache backend is configured."""

    if _cache is None or not romanized.strip():
        return
    try:
        _ = _cache.upsert_romanized_name(original, romanized.strip(), source=source)
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.warning("Failed to cache romanized name for '%s': %s", original, exc)


__all__ = [
    "RomanizationCache",
    "configure_cache",
    "read_cached_name",
    "save_cached_name",
]
