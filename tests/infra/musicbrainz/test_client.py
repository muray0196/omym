from __future__ import annotations

from typing import Any

import pytest


def _wrap_result(data: dict[str, Any] | None) -> Any:
    """Create a lightweight object mimicking _HTTPResult for tests."""
    class R:
        status: int
        headers: dict[str, str]
        data: dict[str, Any] | None

        def __init__(self, d: dict[str, Any] | None) -> None:
            self.status = 200 if d is not None else 0
            self.headers = {}
            self.data = d

    return R(data)


def test_fetch_romanized_name_prefers_ja_latn_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prefers alias with locale=ja-Latn and primary=true over sort-name."""
    from omym.infra.musicbrainz import client

    sample = {
        "artists": [
            {
                "name": "坂本龍一",
                "sort-name": "Sakamoto, Ryuichi",
                "score": "100",
                "aliases": [
                    {"name": "Ryuichi Sakamoto", "locale": "ja-Latn", "primary": "true", "sort-name": "Sakamoto, Ryuichi"},
                    {"name": "坂本龍一", "locale": "ja"},
                ],
            }
        ]
    }

    def fake_get_json(url: str, params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)

    got = client.fetch_romanized_name("坂本龍一")
    assert got == "Sakamoto, Ryuichi"


def test_fetch_romanized_name_falls_back_to_sort_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falls back to artist sort-name when no matching alias exists."""
    from omym.infra.musicbrainz import client

    sample = {
        "artists": [
            {
                "name": "宇多田ヒカル",
                "sort-name": "Utada, Hikaru",
                "score": "98",
                "aliases": [
                    {"name": "Utada", "locale": "en"},  # Not ja-Latn primary
                ],
            }
        ]
    }

    def fake_get_json(url: str, params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)

    got = client.fetch_romanized_name("宇多田ヒカル")
    assert got == "Utada, Hikaru"


def test_fetch_romanized_name_returns_none_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns None when HTTP layer yields no data or no artists list."""
    from omym.infra.musicbrainz import client

    # No data case
    def fake_none(url: str, params: dict[str, str]) -> Any:
        return _wrap_result(None)

    monkeypatch.setattr(client, "_http_get_json", fake_none)
    assert client.fetch_romanized_name("nonexistent") is None

    # Empty artists case
    def fake_empty(url: str, params: dict[str, str]) -> Any:
        return _wrap_result({"artists": []})

    monkeypatch.setattr(client, "_http_get_json", fake_empty)
    assert client.fetch_romanized_name("nonexistent") is None


def test_fetch_romanized_name_accepts_boolean_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accepts primary as boolean True in alias objects."""
    from omym.infra.musicbrainz import client

    sample = {
        "artists": [
            {
                "name": "米津玄師",
                "sort-name": "Yonezu, Kenshi",
                "score": "100",
                "aliases": [
                    {"name": "Kenshi Yonezu", "locale": "ja-Latn", "primary": True},
                ],
            }
        ]
    }

    def fake_get_json(url: str, params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)
    assert client.fetch_romanized_name("米津玄師") == "Kenshi Yonezu"
