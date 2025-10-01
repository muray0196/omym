from __future__ import annotations

from pathlib import Path

from omym.features.path.usecases.renamer import ArtistIdGenerator
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.db.db_manager import DatabaseManager


class TestArtistCacheDAO:
    """Integration tests for ArtistCacheDAO."""

    def _create_dao(self, tmp_path: Path) -> ArtistCacheDAO:
        db_path = tmp_path / "cache.db"
        manager = DatabaseManager(db_path)
        manager.connect()
        assert manager.conn is not None
        return ArtistCacheDAO(manager.conn)

    def test_insert_and_get_artist_id(self, tmp_path: Path) -> None:
        dao = self._create_dao(tmp_path)

        assert dao.insert_artist_id("宇多田ヒカル", "UTADA") is True
        assert dao.get_artist_id("宇多田ヒカル") == "UTADA"

    def test_upsert_romanized_inserts_when_missing(self, tmp_path: Path) -> None:
        dao = self._create_dao(tmp_path)

        assert dao.upsert_romanized_name("宇多田ヒカル", "Hikaru Utada", source="musicbrainz") is True
        assert dao.get_romanized_name("宇多田ヒカル") == "Hikaru Utada"
        # Row should exist even before ID generation; later updates may overwrite default ID
        assert dao.get_artist_id("宇多田ヒカル") == ArtistIdGenerator.DEFAULT_ID

    def test_upsert_romanized_updates_existing_row(self, tmp_path: Path) -> None:
        dao = self._create_dao(tmp_path)

        # Insert initial ID then update romanization
        assert dao.insert_artist_id("米津玄師", "YONEZ") is True
        assert dao.upsert_romanized_name("米津玄師", "Kenshi Yonezu") is True
        assert dao.get_romanized_name("米津玄師") == "Kenshi Yonezu"
        # Ensure artist ID is preserved after romanization update
        assert dao.get_artist_id("米津玄師") == "YONEZ"

        # Update romanized name again and ensure ID still intact
        assert dao.upsert_romanized_name("米津玄師", "Yonezu Kenshi", source="manual") is True
        assert dao.get_romanized_name("米津玄師") == "Yonezu Kenshi"
        assert dao.get_artist_id("米津玄師") == "YONEZ"

    def test_list_romanizations_returns_sorted_and_normalized_rows(self, tmp_path: Path) -> None:
        dao = self._create_dao(tmp_path)

        assert dao.insert_artist_id("Perfume", "PERF") is True
        assert dao.upsert_romanized_name("beta", "Beta", source=None) is True
        assert dao.upsert_romanized_name("Alpha", "Alpha", source="manual") is True

        rows = dao.list_romanizations()

        assert [row[0] for row in rows] == ["Alpha", "beta", "Perfume"]

        alpha_row = rows[0]
        assert alpha_row[1] == "Alpha"
        assert alpha_row[2] == "manual"
        assert alpha_row[3] is not None

        perfume_row = next(row for row in rows if row[0] == "Perfume")
        assert perfume_row[1] is None
        assert perfume_row[2] is None
        assert perfume_row[3] is None

        beta_row = rows[1]
        assert beta_row[1] == "Beta"
        assert beta_row[2] == "musicbrainz"
        assert beta_row[3] is not None
