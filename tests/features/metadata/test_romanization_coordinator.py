"""tests/features/metadata/test_romanization_coordinator.py
Where: tests/features/metadata/test_romanization_coordinator.py
What: Validate romanization coordinator cache handling with cached values.
Why: Document current behaviour when cached values bypass MusicBrainz queries.
Assumptions:
- RomanizationCoordinator keeps `_romanizer` as the active ArtistRomanizer instance.
Trade-offs:
- Casting stubs through `object` avoids refactoring production constructors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from omym.config.artist_name_preferences import ArtistNamePreferenceRepository
from omym.features.metadata.usecases.extraction.romanization import RomanizationCoordinator
from omym.features.metadata.usecases.ports import ArtistCachePort


class _StubPreferences:
    """Lightweight stand-in for ArtistNamePreferenceRepository."""

    def ensure_placeholder(self, raw_artist: str) -> None:  # pragma: no cover - trivial
        del raw_artist
        return None

    def resolve(self, raw_artist: str | None) -> str | None:  # pragma: no cover - trivial
        del raw_artist
        return None

    def snapshot(self) -> dict[str, str]:  # pragma: no cover - trivial
        return {}


@dataclass
class _StubArtistCache(ArtistCachePort):
    """In-memory cache stub capturing persisted romanizations."""

    cached: dict[str, str]
    last_upsert: tuple[str, str, str | None] | None = None

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        self.cached[artist_name] = artist_id
        return True

    def get_artist_id(self, artist_name: str) -> str | None:
        return self.cached.get(artist_name)

    def get_romanized_name(self, artist_name: str) -> str | None:
        return self.cached.get(artist_name)

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        self.cached[artist_name] = romanized_name
        self.last_upsert = (artist_name, romanized_name, source)
        return True

    def clear_cache(self) -> bool:
        self.cached.clear()
        self.last_upsert = None
        return True


def _as_preferences_stub() -> ArtistNamePreferenceRepository:
    stub = _StubPreferences()
    return cast(ArtistNamePreferenceRepository, cast(object, stub))


@pytest.fixture
def coordinator_components() -> tuple[RomanizationCoordinator, _StubArtistCache]:
    cache = _StubArtistCache(cached={"雀が原中学卓球部": "雀が原中学卓球部"})
    preferences = _as_preferences_stub()
    coordinator = RomanizationCoordinator(preferences=preferences, artist_cache=cache)

    romanizer = getattr(coordinator, "_romanizer")

    def _detector(_: str) -> str:
        return "ja"

    def _transliterator(text: str) -> str:
        replacements = {"雀が原中学卓球部": "Suzumegarasu Chugaku Takkyubu"}
        return replacements.get(text, text)

    romanizer.language_detector = _detector  # type: ignore[attr-defined]
    romanizer.transliterator = _transliterator  # type: ignore[attr-defined]
    return coordinator, cache


def test_non_latin_cache_returns_cached_value(
    coordinator_components: tuple[RomanizationCoordinator, _StubArtistCache]
) -> None:
    """Existing cache entries are returned even when non-Latin."""

    target = "雀が原中学卓球部"

    coordinator, cache = coordinator_components
    coordinator.ensure_scheduled(target)
    result = coordinator.await_result(target)

    assert result == target
    romanizer = getattr(coordinator, "_romanizer")
    assert romanizer.consume_last_result_source() is None  # type: ignore[attr-defined]
    assert cache.last_upsert is None
