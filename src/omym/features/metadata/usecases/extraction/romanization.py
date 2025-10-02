"""Romanization coordination utilities.

Where: src/omym/features/metadata/usecases/extraction/romanization.py
What: Coordinate artist name romanization across preferences, cache, and remote fetches.
Why: Isolate asynchronous romanization concerns away from the main processor logic.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import unicodedata
from typing import Callable

from omym.platform.logging import logger
from omym.platform.musicbrainz.client import fetch_romanized_name

from omym.config.artist_name_preferences import ArtistNamePreferenceRepository
from ..ports import ArtistCachePort
from .artist_romanizer import ArtistRomanizer
from .track_metadata_extractor import MetadataExtractor


class RomanizationCoordinator:
    """Manage asynchronous romanization of artist names."""

    def __init__(
        self,
        preferences: ArtistNamePreferenceRepository,
        artist_cache: ArtistCachePort,
        *,
        executor_factory: Callable[[], ThreadPoolExecutor] | None = None,
    ) -> None:
        self._preferences: ArtistNamePreferenceRepository = preferences
        self._artist_cache: ArtistCachePort = artist_cache
        self._executor: ThreadPoolExecutor = (
            executor_factory()
            if executor_factory
            else ThreadPoolExecutor(max_workers=1, thread_name_prefix="mb-romanizer")
        )
        self._romanizer: ArtistRomanizer = ArtistRomanizer(
            fetcher=self._fetch_with_persistent_cache
        )
        MetadataExtractor.configure_romanizer(self._romanizer)
        self._futures: dict[str, Future[str]] = {}

    def _fetch_with_persistent_cache(self, name: str) -> str | None:
        trimmed = name.strip()
        if not trimmed:
            return None

        self._preferences.ensure_placeholder(trimmed)
        preferred = self._preferences.resolve(trimmed)
        if preferred is not None:
            self._romanizer.record_fetch_context(
                source="user_preference",
                original=trimmed,
                value=preferred,
            )
            logger.info(
                "Using user-defined name preference for '%s' -> '%s'",
                trimmed,
                preferred,
            )
            return preferred

        try:
            cached = self._artist_cache.get_romanized_name(trimmed)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to consult persistent romanization cache for '%s': %s",
                trimmed,
                exc,
            )
            cached = None

        if cached:
            self._romanizer.record_fetch_context(
                source="cache",
                original=trimmed,
                value=cached,
            )
            return cached

        result = fetch_romanized_name(name)
        self._romanizer.record_fetch_context(
            source="musicbrainz",
            original=trimmed,
            value=result,
        )
        return result

    @staticmethod
    def _value_contains_non_latin(text: str) -> bool:
        """Detect non-Latin characters similarly to ArtistRomanizer."""

        for char in text:
            if char.isspace() or char == ",":
                continue
            if char.isascii():
                continue
            try:
                name = unicodedata.name(char)
            except ValueError:
                return True
            if "LATIN" not in name:
                return True
        return False

    def ensure_scheduled(self, name: str) -> None:
        """Schedule a romanization task if needed."""

        trimmed = name.strip()
        if not trimmed or trimmed in self._futures:
            return

        preferred = self._preferences.resolve(trimmed)
        if preferred is not None:
            preferred_future: Future[str] = Future()
            preferred_future.set_result(preferred)
            self._futures[trimmed] = preferred_future
            logger.debug("Using artist name preference for '%s' during scheduling", trimmed)
            return

        cached_value: str | None = None
        try:
            cached_value = self._artist_cache.get_romanized_name(trimmed)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to read cached romanized name for '%s': %s", trimmed, exc)

        if cached_value:
            if self._value_contains_non_latin(cached_value):
                logger.debug(
                    "Discarding non-Latin cached romanization for '%s'", trimmed
                )
            else:
                cached_future: Future[str] = Future()
                cached_future.set_result(cached_value)
                self._futures[trimmed] = cached_future
                logger.debug("Using persisted romanization cache for '%s'", trimmed)
                return

        def _romanize() -> str:
            return self._romanizer.romanize_name(trimmed) or trimmed

        logger.debug("Scheduling romanization task for '%s'", trimmed)
        self._futures[trimmed] = self._executor.submit(_romanize)

    def await_result(self, name: str) -> str:
        """Wait for a romanized name result, caching it when successful."""

        trimmed = name.strip()
        if not trimmed:
            return name

        future = self._futures.get(trimmed)
        if future is None:
            self.ensure_scheduled(trimmed)
            future = self._futures.get(trimmed)
        if future is None:
            return name

        try:
            romanized = future.result()
            if romanized != trimmed:
                source = self._romanizer.consume_last_result_source()
                _ = self._artist_cache.upsert_romanized_name(trimmed, romanized, source=source)
            else:
                _ = self._romanizer.consume_last_result_source()
            return romanized
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Romanization future failed for '%s': %s", trimmed, exc)
            return name

    def shutdown(self) -> None:
        """Shutdown the executor gracefully."""

        self._executor.shutdown(wait=False)

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Expose the underlying executor for cleanup hooks."""

        return self._executor

    @property
    def futures(self) -> dict[str, Future[str]]:
        """Expose cached futures for diagnostics and tests."""

        return self._futures


__all__ = ["RomanizationCoordinator"]
