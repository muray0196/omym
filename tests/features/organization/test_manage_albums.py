"""Tests for the album management system."""

import sqlite3

import pytest

from omym.features.organization import AlbumManager, AlbumGroup
from omym.features.organization.usecases.ports import (
    AlbumRecord,
    AlbumRepositoryPort,
)


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Create a test database connection.

    Returns:
        Connection: SQLite database connection.
    """
    conn = sqlite3.connect(":memory:")
    with conn:
        _ = conn.executescript(
            """
            CREATE TABLE albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_name TEXT NOT NULL,
                album_artist TEXT NOT NULL,
                year INTEGER,
                total_tracks INTEGER,
                total_discs INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (album_name, album_artist)
            );

            CREATE TABLE track_positions (
                album_id INTEGER NOT NULL,
                disc_number INTEGER NOT NULL,
                track_number INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (album_id, disc_number, track_number),
                FOREIGN KEY (album_id) REFERENCES albums (id)
            );
            """
        )
    return conn


@pytest.fixture
def album_manager(conn: sqlite3.Connection) -> AlbumManager:
    """Create a test album manager.

    Args:
        conn: SQLite database connection.

    Returns:
        AlbumManager: Album manager instance.
    """
    return AlbumManager(conn)


def test_process_files_single_album(album_manager: AlbumManager) -> None:
    """Test processing files for a single album."""
    files: dict[str, dict[str, str | None]] = {
        "hash1": {
            "album": "Test Album",
            "album_artist": "Test Artist",
            "year": "2020",
            "disc_number": "1",
            "track_number": "1",
            "total_tracks": "2",
            "total_discs": "1",
        },
        "hash2": {
            "album": "Test Album",
            "album_artist": "Test Artist",
            "year": "2020",
            "disc_number": "1",
            "track_number": "2",
            "total_tracks": "2",
            "total_discs": "1",
        },
    }

    album_groups, warnings = album_manager.process_files(files)

    assert len(warnings) == 0
    assert len(album_groups) == 1

    group = album_groups[0]
    assert isinstance(group, AlbumGroup)
    assert isinstance(group.album_info, AlbumRecord)
    assert group.album_info.album_name == "Test Album"
    assert group.album_info.album_artist == "Test Artist"
    assert group.album_info.year == 2020
    assert group.album_info.total_tracks == 2
    assert group.album_info.total_discs == 1
    assert isinstance(group.file_hashes, set)
    assert group.file_hashes == {"hash1", "hash2"}
    assert isinstance(group.warnings, list)
    assert len(group.warnings) == 0


def test_process_files_multiple_albums(album_manager: AlbumManager) -> None:
    """Test processing files for multiple albums."""
    files: dict[str, dict[str, str | None]] = {
        "hash1": {
            "album": "Album 1",
            "album_artist": "Artist 1",
            "year": "2020",
            "disc_number": "1",
            "track_number": "1",
            "total_tracks": "1",
            "total_discs": "1",
        },
        "hash2": {
            "album": "Album 2",
            "album_artist": "Artist 2",
            "year": "2021",
            "disc_number": "1",
            "track_number": "1",
            "total_tracks": "1",
            "total_discs": "1",
        },
    }

    album_groups, warnings = album_manager.process_files(files)

    assert len(warnings) == 0
    assert len(album_groups) == 2

    # Check first album
    group1 = next(g for g in album_groups if g.album_info.album_name == "Album 1")
    assert isinstance(group1, AlbumGroup)
    assert isinstance(group1.album_info, AlbumRecord)
    assert group1.album_info.album_artist == "Artist 1"
    assert group1.album_info.year == 2020
    assert group1.album_info.total_tracks == 1
    assert group1.album_info.total_discs == 1
    assert isinstance(group1.file_hashes, set)
    assert group1.file_hashes == {"hash1"}
    assert isinstance(group1.warnings, list)
    assert len(group1.warnings) == 0

    # Check second album
    group2 = next(g for g in album_groups if g.album_info.album_name == "Album 2")
    assert isinstance(group2, AlbumGroup)
    assert isinstance(group2.album_info, AlbumRecord)
    assert group2.album_info.album_artist == "Artist 2"
    assert group2.album_info.year == 2021
    assert group2.album_info.total_tracks == 1
    assert group2.album_info.total_discs == 1
    assert isinstance(group2.file_hashes, set)
    assert group2.file_hashes == {"hash2"}
    assert isinstance(group2.warnings, list)
    assert len(group2.warnings) == 0


def test_process_files_missing_metadata(album_manager: AlbumManager) -> None:
    """Test processing files with missing metadata."""
    files: dict[str, dict[str, str | None]] = {
        "hash1": {
            "album": "Test Album",
            "album_artist": "Test Artist",
            "year": "2020",
        },
        "hash2": {
            "album": "Test Album",
            "album_artist": "Test Artist",
            "disc_number": "1",
            "track_number": "1",
        },
        "hash3": {
            "album": "Test Album",
        },
    }

    album_groups, warnings = album_manager.process_files(files)

    assert len(warnings) == 1
    assert "Missing album information" in warnings[0]
    assert "album_artist=None" in warnings[0]
    assert len(album_groups) == 1

    group = album_groups[0]
    assert isinstance(group, AlbumGroup)
    assert isinstance(group.album_info, AlbumRecord)
    assert group.album_info.album_name == "Test Album"
    assert group.album_info.album_artist == "Test Artist"
    assert isinstance(group.file_hashes, set)
    assert group.file_hashes == {"hash1", "hash2"}
    assert isinstance(group.warnings, list)
    assert len(group.warnings) == 1
    assert "Missing track position" in group.warnings[0]


def test_process_files_track_continuity(album_manager: AlbumManager) -> None:
    """Test track continuity checking."""
    files: dict[str, dict[str, str | None]] = {
        "hash1": {
            "album": "Test Album",
            "album_artist": "Test Artist",
            "disc_number": "1",
            "track_number": "1",
            "total_tracks": "3",
            "total_discs": "1",
        },
        "hash2": {
            "album": "Test Album",
            "album_artist": "Test Artist",
            "disc_number": "1",
            "track_number": "3",
            "total_tracks": "3",
            "total_discs": "1",
        },
    }

    album_groups, warnings = album_manager.process_files(files)

    assert len(warnings) == 0
    assert len(album_groups) == 1

    group = album_groups[0]
    assert isinstance(group, AlbumGroup)
    assert isinstance(group.album_info, AlbumRecord)
    assert isinstance(group.warnings, list)
    assert len(group.warnings) == 1
    assert "Missing tracks in disc 1: [2]" == group.warnings[0]


def test_get_earliest_year(album_manager: AlbumManager) -> None:
    """Test getting the earliest year from files.

    Note:
        This test accesses a protected method for testing purposes.
        The method is protected to prevent external access while allowing testing.
    """
    files: dict[str, dict[str, str | None]] = {
        "hash1": {"year": "2020"},
        "hash2": {"year": "2021"},
        "hash3": {"year": "invalid"},
        "hash4": {},
    }
    file_hashes: set[str] = {"hash1", "hash2", "hash3", "hash4"}

    year = album_manager._get_earliest_year(file_hashes, files)  # pyright: ignore[reportPrivateUsage]
    assert year == 2020


def test_album_manager_accepts_port_injection() -> None:
    """AlbumManager should delegate persistence to an injected repository port."""

    class StubAlbumPort(AlbumRepositoryPort):
        def __init__(self) -> None:
            self.records: dict[tuple[str, str], AlbumRecord] = {}
            self.track_positions: dict[int, list[tuple[int, int, str]]] = {}
            self.next_id: int = 1
            self.continuity_calls: list[int] = []

        def get_album(self, album_name: str, album_artist: str) -> AlbumRecord | None:
            return self.records.get((album_name, album_artist))

        def insert_album(
            self,
            album_name: str,
            album_artist: str,
            year: int | None = None,
            total_tracks: int | None = None,
            total_discs: int | None = None,
        ) -> int | None:
            identifier = self.next_id
            self.next_id += 1
            self.records[(album_name, album_artist)] = AlbumRecord(
                id=identifier,
                album_name=album_name,
                album_artist=album_artist,
                year=year,
                total_tracks=total_tracks,
                total_discs=total_discs,
            )
            return identifier

        def insert_track_position(
            self,
            album_id: int,
            disc_number: int,
            track_number: int,
            file_hash: str,
        ) -> bool:
            self.track_positions.setdefault(album_id, []).append((disc_number, track_number, file_hash))
            return True

        def check_track_continuity(self, album_id: int) -> tuple[bool, list[str]]:
            self.continuity_calls.append(album_id)
            return True, []

    port = StubAlbumPort()
    manager = AlbumManager(album_port=port)

    files: dict[str, dict[str, str | None]] = {
        "hash": {
            "album": "Injection",
            "album_artist": "Artist",
            "year": "2022",
            "disc_number": "1",
            "track_number": "1",
            "total_tracks": "1",
            "total_discs": "1",
        }
    }

    groups, warnings = manager.process_files(files)

    assert warnings == []
    assert len(groups) == 1
    stored_album = port.records[("Injection", "Artist")]
    assert stored_album.year == 2022
    assert port.track_positions[stored_album.id] == [(1, 1, "hash")]
    assert port.continuity_calls == [stored_album.id]
