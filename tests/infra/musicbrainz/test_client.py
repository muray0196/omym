from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

@pytest.fixture(autouse=True)
def reset_romanization_cache() -> Iterator[None]:
    from omym.infra.musicbrainz import client

    client.configure_romanization_cache(None)
    yield
    client.configure_romanization_cache(None)


class _DummyCache:
    def __init__(self, data: dict[str, str] | None = None) -> None:
        self.data: dict[str, str] = {k.lower(): v for k, v in (data or {}).items()}
        self.upserts: list[tuple[str, str, str | None]] = []

    def get_romanized_name(self, artist_name: str) -> str | None:
        return self.data.get(artist_name.strip().lower())

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        self.data[artist_name.strip().lower()] = romanized_name
        self.upserts.append((artist_name.strip(), romanized_name, source))
        return True


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

    def fake_get_json(_url: str, _params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)

    got = client.fetch_romanized_name("坂本龍一")
    assert got == "Sakamoto, Ryuichi"


def test_fetch_romanized_name_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from omym.infra.musicbrainz import client

    cache = _DummyCache({"宇多田ヒカル": "Hikaru Utada"})
    client.configure_romanization_cache(cache)

    def fake_http(_url: str, _params: dict[str, str]) -> Any:  # pragma: no cover - should not run
        raise AssertionError("HTTP should not be called when cache hits")

    monkeypatch.setattr(client, "_http_get_json", fake_http)

    got = client.fetch_romanized_name("宇多田ヒカル")
    assert got == "Hikaru Utada"


def test_fetch_romanized_name_caches_new_values(monkeypatch: pytest.MonkeyPatch) -> None:
    from omym.infra.musicbrainz import client

    cache = _DummyCache()
    client.configure_romanization_cache(cache)

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

    def fake_get_json(_url: str, _params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)

    got = client.fetch_romanized_name("米津玄師")
    assert got == "Kenshi Yonezu"
    assert cache.get_romanized_name("米津玄師") == "Kenshi Yonezu"
    assert ("米津玄師", "Kenshi Yonezu", "musicbrainz") in cache.upserts


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

    def fake_get_json(_url: str, _params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)

    got = client.fetch_romanized_name("宇多田ヒカル")
    assert got == "Utada, Hikaru"


def test_fetch_romanized_name_returns_none_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns None when HTTP layer yields no data or no artists list."""
    from omym.infra.musicbrainz import client

    # No data case
    def fake_none(_url: str, _params: dict[str, str]) -> Any:
        return _wrap_result(None)

    monkeypatch.setattr(client, "_http_get_json", fake_none)
    assert client.fetch_romanized_name("nonexistent") is None

    # Empty artists case
    def fake_empty(_url: str, _params: dict[str, str]) -> Any:
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

    def fake_get_json(_url: str, _params: dict[str, str]) -> Any:
        return _wrap_result(sample)

    monkeypatch.setattr(client, "_http_get_json", fake_get_json)
    assert client.fetch_romanized_name("米津玄師") == "Kenshi Yonezu"
