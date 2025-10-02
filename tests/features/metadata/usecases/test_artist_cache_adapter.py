# Where: tests/features/metadata/usecases/test_artist_cache_adapter.py
# What: Regression tests for dry-run artist cache adapter persistence behaviour.
# Why: Ensure plan mode writes reach SQLite so later organise runs reuse identifiers.
# Assumptions:
# - DatabaseManager initialises the artist_cache schema on connect.
# - ArtistCacheDAO enforces upsert semantics for IDs and romanised names.
# Trade-offs:
# - Tests rely on SQLite writes, incurring minor IO cost but covering persistence.

from __future__ import annotations

from pathlib import Path
from sqlite3 import Connection
from typing import cast

from omym.features.metadata.usecases.extraction.artist_cache_adapter import DryRunArtistCacheAdapter
from omym.features.path.usecases.renamer import ArtistIdGenerator
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.db.db_manager import DatabaseManager


def _build_adapter(
    tmp_path: Path,
) -> tuple[DatabaseManager, Connection, DryRunArtistCacheAdapter]:
    db_path = tmp_path / "artist_cache.db"
    manager = DatabaseManager(db_path)
    manager.connect()
    conn = manager.conn
    assert conn is not None
    adapter = DryRunArtistCacheAdapter(ArtistCacheDAO(conn))
    return manager, conn, adapter


def test_dry_run_adapter_persists_artist_ids(tmp_path: Path) -> None:
    manager, conn, adapter = _build_adapter(tmp_path)
    try:
        expected_id = ArtistIdGenerator.generate("John Smith")
        assert adapter.insert_artist_id("John Smith", expected_id) is True
        assert adapter.get_artist_id("John Smith") == expected_id

        cursor = conn.cursor()
        _ = cursor.execute(
            "SELECT artist_id FROM artist_cache WHERE artist_name = ?",
            ("John Smith",),
        )
        row = cursor.fetchone()
        assert row == (expected_id,)
    finally:
        manager.close()


def test_dry_run_adapter_persists_romanizations(tmp_path: Path) -> None:
    manager, conn, adapter = _build_adapter(tmp_path)
    try:
        assert adapter.upsert_romanized_name("宇多田ヒカル", "Utada Hikaru", source="musicbrainz") is True
        assert adapter.get_romanized_name("宇多田ヒカル") == "Utada Hikaru"

        cursor = conn.cursor()
        _ = cursor.execute(
            "SELECT romanized_name, romanization_source FROM artist_cache WHERE artist_name = ?",
            ("宇多田ヒカル",),
        )
        row = cursor.fetchone()
        assert row == ("Utada Hikaru", "musicbrainz")
    finally:
        manager.close()


class _FailingArtistCacheDAO:
    """Stub that simulates a delegate raising on persistence."""

    def __init__(self) -> None:
        self.conn: Connection | None = None

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        del artist_name, artist_id
        raise RuntimeError("boom")

    def get_artist_id(self, artist_name: str) -> str | None:
        del artist_name
        return None

    def get_romanized_name(self, artist_name: str) -> str | None:
        del artist_name
        return None

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        del artist_name, romanized_name, source
        raise RuntimeError("boom")

    def clear_cache(self) -> bool:
        raise RuntimeError("boom")


def test_dry_run_adapter_falls_back_to_memory_when_delegate_fails() -> None:
    failing_delegate = cast(ArtistCacheDAO, cast(object, _FailingArtistCacheDAO()))
    adapter = DryRunArtistCacheAdapter(failing_delegate)

    assert adapter.insert_artist_id("Alice", "ALICE") is True
    assert adapter.get_artist_id("Alice") == "ALICE"

    assert adapter.upsert_romanized_name("Bob", "Bob", source="manual") is True
    assert adapter.get_romanized_name("Bob") == "Bob"

    assert adapter.clear_cache() is False
    assert adapter.get_artist_id("Alice") is None
    assert adapter.get_romanized_name("Bob") is None
