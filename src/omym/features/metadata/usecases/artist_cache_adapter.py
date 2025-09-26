"""src/omym/features/metadata/usecases/artist_cache_adapter.py
What: In-memory wrapper to make artist cache writes safe during dry runs.
Why: Keep MusicProcessor focused on orchestration and reuse adapter elsewhere if needed.
"""

from __future__ import annotations

from sqlite3 import Connection
from typing import ClassVar

from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO


class DryRunArtistCacheAdapter:
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
        return True


__all__ = ["DryRunArtistCacheAdapter"]
