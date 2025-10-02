"""Unit tests for the artist preference inspection service."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from omym.application.services.preferences_service import (
    ArtistPreferenceInspector,
    ArtistPreferenceRow,
)
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.db.db_manager import DatabaseManager


@pytest.fixture()
def configured_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ArtistPreferenceInspector, DatabaseManager]:
    """Provision a DAO and preference file for inspection tests."""

    preferences_path = tmp_path / "artist_prefs.toml"
    _ = preferences_path.write_text(
        textwrap.dedent(
            """
            metadata_version = 1

            [defaults]

            [preferences]
            "宇多田ヒカル" = "Utada Hikaru"
            "米津玄師" = ""
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OMYM_ARTIST_NAME_PREFERENCES_PATH", str(preferences_path))

    manager = DatabaseManager(tmp_path / "cache.db")
    manager.connect()
    assert manager.conn is not None
    dao = ArtistCacheDAO(manager.conn)

    # Populate cache data for three artists with varying states.
    assert dao.upsert_romanized_name("宇多田ヒカル", "Utada Hikaru", source="musicbrainz") is True
    assert dao.upsert_romanized_name("東京事変", "Tokyo Incidents", source="manual") is True
    assert dao.insert_artist_id("米津玄師", "YONEZ") is True

    inspector = ArtistPreferenceInspector(dao)
    return inspector, manager


def test_collect_merges_preferences_and_cache(configured_environment: tuple[ArtistPreferenceInspector, DatabaseManager]) -> None:
    inspector, manager = configured_environment

    try:
        rows = inspector.collect(include_all=True)
    finally:
        manager.close()

    assert rows == sorted(rows, key=lambda row: row.artist_name.casefold())

    lookup = {row.artist_name: row for row in rows}

    utada = lookup["宇多田ヒカル"]
    assert isinstance(utada, ArtistPreferenceRow)
    assert utada.preferred_name == "Utada Hikaru"
    assert utada.cached_name == "Utada Hikaru"
    assert utada.source == "musicbrainz"

    yonezu = lookup["米津玄師"]
    assert yonezu.preferred_name is None
    assert yonezu.cached_name is None
    assert yonezu.source is None

    tokyo_incidents = lookup["東京事変"]
    assert tokyo_incidents.preferred_name is None
    assert tokyo_incidents.cached_name == "Tokyo Incidents"
    assert tokyo_incidents.source == "manual"


def test_collect_filters_missing_entries(configured_environment: tuple[ArtistPreferenceInspector, DatabaseManager]) -> None:
    inspector, manager = configured_environment

    try:
        rows = inspector.collect(include_all=False)
    finally:
        manager.close()

    names = {row.artist_name for row in rows}
    assert names == {"東京事変"}

    assert all(row.cached_name is not None for row in rows)
    assert all(row.preferred_name is None or row.preferred_name != row.cached_name for row in rows)


def test_collect_filters_ascii_untracked(configured_environment: tuple[ArtistPreferenceInspector, DatabaseManager]) -> None:
    inspector, manager = configured_environment

    try:
        rows = inspector.collect(include_all=False)
    finally:
        manager.close()

    ascii_names = {row.artist_name for row in rows if row.artist_name.isascii()}
    assert not ascii_names


def test_collect_includes_transliteration_ascii(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transliteration fallbacks should surface in missing view even if ASCII."""

    preferences_path = tmp_path / "artist_prefs.toml"
    _ = preferences_path.write_text(
        textwrap.dedent(
            """
            metadata_version = 1

            [defaults]

            [preferences]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OMYM_ARTIST_NAME_PREFERENCES_PATH", str(preferences_path))

    manager = DatabaseManager(tmp_path / "cache.db")
    manager.connect()
    try:
        assert manager.conn is not None
        dao = ArtistCacheDAO(manager.conn)
        assert dao.upsert_romanized_name("Kana Artist", "Kana Artist", source="transliteration") is True

        inspector = ArtistPreferenceInspector(dao)
        rows = inspector.collect(include_all=False)
    finally:
        manager.close()

    lookup = {row.artist_name: row for row in rows}
    transliteration_row = lookup.get("Kana Artist")
    assert transliteration_row is not None
    assert transliteration_row.cached_name == "Kana Artist"
    assert transliteration_row.source == "transliteration"
