"""
Summary: SQLite-backed album repository adapter implementing the organization port.
Why: Encapsulate AlbumDAO interactions outside of the use case for clear layering.
"""

from __future__ import annotations

from typing import final

from omym.platform.db.daos.albums_dao import AlbumDAO

from ..usecases.ports import AlbumRecord, AlbumRepositoryPort


@final
class AlbumDaoAdapter(AlbumRepositoryPort):
    """Adapter projecting ``AlbumDAO`` behaviour through the album repository port."""

    def __init__(self, dao: AlbumDAO) -> None:
        """Store the DAO dependency."""
        self._dao = dao

    def get_album(self, album_name: str, album_artist: str) -> AlbumRecord | None:
        record = self._dao.get_album(album_name, album_artist)
        if record is None:
            return None
        return AlbumRecord(
            id=record.id,
            album_name=record.album_name,
            album_artist=record.album_artist,
            year=record.year,
            total_tracks=record.total_tracks,
            total_discs=record.total_discs,
        )

    def insert_album(
        self,
        album_name: str,
        album_artist: str,
        year: int | None = None,
        total_tracks: int | None = None,
        total_discs: int | None = None,
    ) -> int | None:
        return self._dao.insert_album(album_name, album_artist, year, total_tracks, total_discs)

    def insert_track_position(
        self,
        album_id: int,
        disc_number: int,
        track_number: int,
        file_hash: str,
    ) -> bool:
        return self._dao.insert_track_position(album_id, disc_number, track_number, file_hash)

    def check_track_continuity(self, album_id: int) -> tuple[bool, list[str]]:
        return self._dao.check_track_continuity(album_id)
