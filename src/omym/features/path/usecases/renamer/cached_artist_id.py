"""
Summary: Wrap artist ID generation with caching and validation helpers.
Why: Keep persistence coordination isolated while exposing a simple interface to use cases.
"""

from __future__ import annotations

from typing import final

from omym.platform.logging import logger

from ..ports import ArtistCacheWriter
from .artist_id import ArtistIdGenerator


@final
class CachedArtistIdGenerator:
    """Generate and cache artist IDs."""

    def __init__(self, dao: ArtistCacheWriter):
        self.dao = dao

    def generate(self, artist_name: str | None) -> str:
        """Generate or retrieve a cached artist ID."""

        try:
            if not artist_name or not artist_name.strip():
                return ArtistIdGenerator.DEFAULT_ID

            normalized_name = artist_name.strip()

            cached_id = self.dao.get_artist_id(normalized_name)
            if cached_id:
                if self._is_valid_id(cached_id):
                    return cached_id
                logger.warning(
                    "Found invalid cached ID '%s' for artist '%s', regenerating",
                    cached_id,
                    normalized_name,
                )

            new_id = ArtistIdGenerator.generate(normalized_name)

            if self._should_cache(new_id):
                retry_count = 3
                while retry_count > 0:
                    try:
                        if self.dao.insert_artist_id(normalized_name, new_id):
                            logger.debug(
                                "Successfully cached artist ID '%s' for '%s'",
                                new_id,
                                normalized_name,
                            )
                            break
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.warning(
                            "Failed to cache artist ID for '%s' (attempt %d): %s",
                            normalized_name,
                            4 - retry_count,
                            exc,
                        )
                    retry_count -= 1
                    if retry_count > 0:
                        import time

                        time.sleep(0.1)
            else:
                logger.debug(
                    "Skipping cache for invalid/special artist ID '%s' for '%s'",
                    new_id,
                    normalized_name,
                )

            return new_id

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to generate/cache artist ID for '%s': %s",
                artist_name,
                exc,
            )
            return ArtistIdGenerator.DEFAULT_ID

    @staticmethod
    def _is_valid_id(artist_id: str) -> bool:
        if not artist_id:
            return False

        if len(artist_id) > ArtistIdGenerator.ID_LENGTH:
            return False

        if artist_id in [ArtistIdGenerator.DEFAULT_ID, ArtistIdGenerator.FALLBACK_ID]:
            return True

        return bool(ArtistIdGenerator.KEEP_CHARS.sub("", artist_id) == artist_id)

    def _should_cache(self, artist_id: str) -> bool:
        return (
            artist_id
            not in [ArtistIdGenerator.DEFAULT_ID, ArtistIdGenerator.FALLBACK_ID]
            and self._is_valid_id(artist_id)
            and all(char.isalnum() or char == "-" for char in artist_id)
        )


__all__ = ["CachedArtistIdGenerator"]
