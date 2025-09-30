"""Where: src/omym/platform/musicbrainz/romanization.py
What: Helpers for selecting the best romanized artist representation.
Why: Separate payload interpretation from HTTP and cache concerns.
"""

from __future__ import annotations

from typing import Any, cast


def truthy(value: Any) -> bool:
    """Return True when the value represents an affirmative flag."""

    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def choose_romanized_alias(aliases: list[dict[str, Any]] | None) -> str | None:
    """Prefer the ja-Latn primary alias when available."""

    if not aliases:
        return None
    for alias in aliases:
        if alias.get("locale") == "ja-Latn" and truthy(alias.get("primary")):
            return alias.get("sort-name") or alias.get("name")
    return None


def pick_best_artist(artists: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Score-based selection of the most relevant artist entry."""

    if not artists:
        return None
    try:
        return max(artists, key=lambda artist: int(artist.get("score", 0)))
    except Exception:
        return artists[0]


def extract_artist_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Filter the raw payload to a list of artist dictionaries."""

    artists_raw = payload.get("artists")
    if not isinstance(artists_raw, list):
        return []
    artists_raw_list = cast(list[object], artists_raw)
    artists: list[dict[str, Any]] = []
    for entry in artists_raw_list:
        if isinstance(entry, dict):
            artists.append(cast(dict[str, Any], entry))
    return artists


__all__ = [
    "choose_romanized_alias",
    "extract_artist_candidates",
    "pick_best_artist",
    "truthy",
]
