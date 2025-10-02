"""src/omym/application/services/preferences_service.py
What: Aggregate artist preference configuration with cached romanisations.
Why: Centralise reporting rules for downstream presentation layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from omym.config.artist_name_preferences import load_artist_name_preferences
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO

_TRANSLITERATION_SOURCE = "transliteration"


def _is_transliteration(source: str | None) -> bool:
    """Return True when the cached source represents a pykakasi fallback."""

    if source is None:
        return False
    return source.casefold() == _TRANSLITERATION_SOURCE


def _normalize_optional(value: str | None) -> str | None:
    """Strip whitespace and coerce blank strings to ``None``."""

    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _contains_non_ascii(value: str | None) -> bool:
    """Return True when ``value`` contains at least one non-ASCII character."""

    if value is None:
        return False
    return not value.isascii()


@dataclass(frozen=True, slots=True)
class ArtistPreferenceRow:
    """Snapshot row combining configuration and cache state for one artist."""

    artist_name: str
    preferred_name: str | None
    cached_name: str | None
    source: str | None


@final
class ArtistPreferenceInspector:
    """Inspect persistent cache and user overrides for reporting purposes."""

    def __init__(self, cache_dao: ArtistCacheDAO) -> None:
        self._cache_dao = cache_dao

    def collect(self, *, include_all: bool) -> list[ArtistPreferenceRow]:
        """Return sorted preference rows according to configured business rules."""

        repository = load_artist_name_preferences()
        preferences_snapshot = repository.snapshot()

        preference_index: dict[str, tuple[str, str | None]] = {}
        for raw_name, configured in preferences_snapshot.items():
            cleaned_key = raw_name.strip()
            if not cleaned_key:
                continue
            preference_index[cleaned_key.casefold()] = (cleaned_key, _normalize_optional(configured))

        cache_index: dict[str, tuple[str, str | None, str | None]] = {}
        for artist_name, romanized, source, _ in self._cache_dao.list_romanizations():
            cleaned_name = artist_name.strip()
            if not cleaned_name:
                continue
            normalized_key = cleaned_name.casefold()
            cache_index[normalized_key] = (
                cleaned_name,
                _normalize_optional(romanized),
                _normalize_optional(source),
            )

        all_keys = sorted(preference_index.keys() | cache_index.keys())

        rows: list[ArtistPreferenceRow] = []
        for key in all_keys:
            pref_entry = preference_index.get(key)
            cache_entry = cache_index.get(key)

            display_name = (
                pref_entry[0]
                if pref_entry is not None
                else cache_entry[0]
                if cache_entry is not None
                else None
            )
            if display_name is None:
                continue

            preferred_name = pref_entry[1] if pref_entry is not None else None
            cached_name = cache_entry[1] if cache_entry is not None else None
            source = cache_entry[2] if cache_entry is not None and cached_name is not None else None

            rows.append(
                ArtistPreferenceRow(
                    artist_name=display_name,
                    preferred_name=preferred_name,
                    cached_name=cached_name,
                    source=source,
                )
            )

        if not include_all:
            rows = [
                row
                for row in rows
                if row.cached_name is not None
                and (row.preferred_name is None or row.preferred_name != row.cached_name)
                and (
                    _contains_non_ascii(row.artist_name)
                    or _contains_non_ascii(row.cached_name)
                    or _is_transliteration(row.source)
                )
            ]

        rows.sort(key=lambda row: row.artist_name.casefold())

        return rows
