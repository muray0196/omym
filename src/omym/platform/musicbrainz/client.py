"""Where: src/omym/platform/musicbrainz/client.py
What: Facade exposing MusicBrainz WS2 romanization helpers.
Why: Delegate specialised responsibilities to focused collaborators while
     retaining the existing public API for downstream code.

This module now delegates specialised responsibilities to smaller helpers:
- ``http_client`` provides retrying HTTP access with rate limiting
- ``romanization`` encapsulates payload selection logic
- ``cache`` offers optional persistence for romanized names
- ``user_agent`` centralises etiquette for outbound requests

The exposed API remains ``fetch_romanized_name`` and
``configure_romanization_cache`` for downstream code.
"""

from __future__ import annotations

from typing import Any, Final, cast

from omym.config.settings import MB_APP_NAME, MB_APP_VERSION, MB_CONTACT

from .cache import (
    RomanizationCache,
    configure_cache,
    read_cached_name,
    save_cached_name,
)
from .http_client import DEFAULT_HTTP_CLIENT, HTTPClient, HTTPResult
from .romanization import (
    choose_romanized_alias,
    extract_artist_candidates,
    pick_best_artist,
)
from .user_agent import configure_client_user_agent, format_user_agent

MB_BASE_URL: Final[str] = "https://musicbrainz.org/ws/2/artist/"
_CACHE_SOURCE: Final[str] = "musicbrainz"
_HTTP_CLIENT: HTTPClient = DEFAULT_HTTP_CLIENT


def _sanitize_musicbrainz_name(value: str) -> str:
    """Collapse MusicBrainz commas that conflict with downstream splitting."""

    return value.replace(", ", " ").strip()


def _http_get_json(url: str, params: dict[str, str]) -> HTTPResult:
    """Thin wrapper kept for tests patching the HTTP boundary."""

    return _HTTP_CLIENT.get_json(url, params)


def configure_romanization_cache(cache: RomanizationCache | None) -> None:
    """Expose cache configuration while hiding the concrete protocol."""

    configure_cache(cache)


def fetch_romanized_name(name: str) -> str | None:
    """Fetch a romanized artist name from MusicBrainz.

    Selection priority:
    1. Alias where ``locale == 'ja-Latn'`` and ``primary == true``
    2. Artist ``sort-name``
    """

    trimmed = name.strip()
    if not trimmed:
        return None

    cached = read_cached_name(trimmed)
    if cached:
        return cached

    result = _http_get_json(MB_BASE_URL, {"query": f"artist:{trimmed}", "fmt": "json"})
    data = result.data
    if data is None:
        return None

    artists = extract_artist_candidates(data)
    if not artists:
        return None

    best = pick_best_artist(artists)
    if best is None:
        return None

    aliases_raw = best.get("aliases")
    aliases: list[dict[str, Any]] | None = None
    if isinstance(aliases_raw, list):
        aliases_raw_list = cast(list[object], aliases_raw)
        filtered_aliases: list[dict[str, Any]] = []
        for alias in aliases_raw_list:
            if isinstance(alias, dict):
                filtered_aliases.append(cast(dict[str, Any], alias))
        aliases = filtered_aliases

    romanized = choose_romanized_alias(aliases)
    if romanized:
        sanitized_alias = _sanitize_musicbrainz_name(romanized)
        if sanitized_alias:
            save_cached_name(trimmed, sanitized_alias, source=_CACHE_SOURCE)
            return sanitized_alias

    sort_name = best.get("sort-name")
    if isinstance(sort_name, str) and sort_name.strip():
        sanitized = _sanitize_musicbrainz_name(sort_name)
        save_cached_name(trimmed, sanitized, source=_CACHE_SOURCE)
        return sanitized

    return None


class MusicBrainzClient:
    """Lightweight MusicBrainz WS2 client.

    Currently provides only the ``fetch_romanized_name`` convenience method.
    """

    def __init__(self, app_name: str, app_version: str, contact: str) -> None:
        self.user_agent: str = format_user_agent(app_name, app_version, contact)
        configure_client_user_agent(self.user_agent)

    def fetch_romanized_name(self, name: str) -> str | None:
        """Instance variant delegating to the module-level implementation."""

        return fetch_romanized_name(name)


_DEFAULT_CLIENT = MusicBrainzClient(MB_APP_NAME, MB_APP_VERSION, MB_CONTACT)


__all__ = [
    "configure_romanization_cache",
    "fetch_romanized_name",
    "MusicBrainzClient",
    "format_user_agent",
]
