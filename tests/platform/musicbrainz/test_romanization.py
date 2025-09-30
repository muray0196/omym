"""Tests for the romanization helper module."""

from __future__ import annotations

from omym.platform.musicbrainz import romanization


def test_choose_romanized_alias_prefers_ja_latn_primary() -> None:
    aliases = [
        {"name": "Utada", "locale": "en"},
        {"name": "Hikaru Utada", "locale": "ja-Latn", "primary": "true"},
    ]

    assert romanization.choose_romanized_alias(aliases) == "Hikaru Utada"


def test_extract_artist_candidates_filters_non_dict_entries() -> None:
    payload = {"artists": [{"name": "米津玄師"}, "invalid", 123]}

    candidates = romanization.extract_artist_candidates(payload)

    assert candidates == [{"name": "米津玄師"}]
