"""
Summary: Dry-run artist cache adapter that persists via a delegate DAO while caching fallback state in memory.
Why: Keep infrastructure-centric artist cache wiring inside the adapters layer to maintain pure use cases.
"""

from __future__ import annotations

from sqlite3 import Connection
from typing import ClassVar

from omym.features.metadata.usecases.ports import ArtistCachePort
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.logging import logger


class DryRunArtistCacheAdapter(ArtistCachePort):
    """Artist cache adapter that avoids persistent writes during dry runs."""

    _DEFAULT_SOURCE: ClassVar[str] = "musicbrainz"

    def __init__(self, delegate: ArtistCacheDAO) -> None:
        self._delegate: ArtistCacheDAO = delegate
        self.conn: Connection = delegate.conn
        self._memory_artist_ids: dict[str, str] = {}
        self._memory_romanized: dict[str, tuple[str, str]] = {}

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        normalized_name = artist_name.strip()
        normalized_id = artist_id.strip()
        if not normalized_name or not normalized_id:
            return False
        self._memory_artist_ids[normalized_name] = normalized_id
        persisted = False
        try:
            persisted = self._delegate.insert_artist_id(normalized_name, normalized_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Dry-run artist cache adapter failed to persist ID for '%s': %s",
                normalized_name,
                exc,
            )
        if not persisted:
            logger.debug(
                "Dry-run artist cache adapter cached ID for '%s' in memory only",
                normalized_name,
            )
        return True

    def get_artist_id(self, artist_name: str) -> str | None:
        normalized_name = artist_name.strip()
        if not normalized_name:
            return None
        in_memory = self._memory_artist_ids.get(normalized_name)
        if in_memory:
            return in_memory
        return self._delegate.get_artist_id(artist_name)

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        normalized_name = artist_name.strip()
        normalized_romanized = romanized_name.strip()
        if not normalized_name or not normalized_romanized:
            return False
        effective_source = (source or self._DEFAULT_SOURCE).strip() or self._DEFAULT_SOURCE
        self._memory_romanized[normalized_name] = (normalized_romanized, effective_source)
        persisted = False
        try:
            persisted = self._delegate.upsert_romanized_name(
                normalized_name,
                normalized_romanized,
                effective_source,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Dry-run artist cache adapter failed to persist romanization for '%s': %s",
                normalized_name,
                exc,
            )
        if not persisted:
            logger.debug(
                "Dry-run artist cache adapter cached romanization for '%s' in memory only",
                normalized_name,
            )
        return True

    def get_romanized_name(self, artist_name: str) -> str | None:
        normalized_name = artist_name.strip()
        if not normalized_name:
            return None
        in_memory = self._memory_romanized.get(normalized_name)
        if in_memory:
            return in_memory[0]
        return self._delegate.get_romanized_name(artist_name)

    def clear_cache(self) -> bool:
        self._memory_artist_ids.clear()
        self._memory_romanized.clear()
        try:
            return self._delegate.clear_cache()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Dry-run artist cache adapter failed to clear delegate cache: %s", exc)
            return False


__all__ = ["DryRunArtistCacheAdapter"]
