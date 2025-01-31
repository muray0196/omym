"""Tests for the path generation system."""

import sqlite3
from pathlib import Path
from collections.abc import Generator

import pytest

from omym.core.path.path_generator import PathGenerator
from omym.db.daos.filter_dao import FilterDAO


@pytest.fixture
def conn() -> Generator[sqlite3.Connection, None, None]:
    """Create a test database connection.

    Yields:
        sqlite3.Connection: A test database connection.
    """
    conn = sqlite3.connect(":memory:")
    with conn:
        _ = conn.executescript(
            """
            CREATE TABLE processing_before (
                file_hash TEXT PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                title TEXT,
                artist TEXT,
                album TEXT,
                album_artist TEXT,
                genre TEXT,
                year INTEGER,
                track_number INTEGER,
                total_tracks INTEGER,
                disc_number INTEGER,
                total_discs INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE processing_after (
                file_hash TEXT PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                target_path TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
            );

            CREATE TABLE filter_hierarchies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (name)
            );

            CREATE TABLE filter_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hierarchy_id INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hierarchy_id) REFERENCES filter_hierarchies (id),
                FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
            );

            CREATE TABLE albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_name TEXT NOT NULL,
                album_artist TEXT NOT NULL,
                year INTEGER,
                total_tracks INTEGER,
                total_discs INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (album_name, album_artist)
            );

            CREATE TABLE track_positions (
                album_id INTEGER NOT NULL,
                disc_number INTEGER NOT NULL,
                track_number INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (album_id, disc_number, track_number),
                FOREIGN KEY (album_id) REFERENCES albums (id),
                FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
            );

            CREATE TABLE artist_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_name TEXT NOT NULL,
                artist_id TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (artist_name)
            );

            CREATE INDEX IF NOT EXISTS idx_albums_name_artist ON albums(album_name, album_artist);
            CREATE INDEX IF NOT EXISTS idx_track_positions_file_hash ON track_positions(file_hash);
            CREATE INDEX IF NOT EXISTS idx_filter_values_file_hash ON filter_values(file_hash);
            CREATE INDEX IF NOT EXISTS idx_filter_values_hierarchy ON filter_values(hierarchy_id);
            CREATE INDEX IF NOT EXISTS idx_artist_cache_name ON artist_cache(artist_name);
            """
        )
    yield conn
    conn.close()


@pytest.fixture
def filter_dao(conn: sqlite3.Connection) -> FilterDAO:
    """Create a test filter DAO.

    Args:
        conn: A test database connection.

    Returns:
        FilterDAO: A test filter DAO.
    """
    return FilterDAO(conn)


@pytest.fixture
def path_generator(conn: sqlite3.Connection) -> PathGenerator:
    """Create a test path generator.

    Args:
        conn: A test database connection.

    Returns:
        PathGenerator: A test path generator.
    """
    return PathGenerator(conn, Path("/test/music"))


def test_generate_paths_single_file(path_generator: PathGenerator, filter_dao: FilterDAO) -> None:
    """Test generating paths for a single file.

    Args:
        path_generator: A test path generator.
        filter_dao: A test filter DAO.
    """
    # Register hierarchies
    hierarchy_id = filter_dao.insert_hierarchy("AlbumArtist", 0)
    assert hierarchy_id is not None

    # Register values
    file_hash = "test_hash"
    assert filter_dao.insert_value(hierarchy_id, file_hash, "Test Artist")

    # Generate paths
    paths = path_generator.generate_paths()
    assert len(paths) == 1

    path_info = paths[0]
    assert path_info.file_hash == file_hash
    assert path_info.relative_path == Path("Test Artist")
    assert len(path_info.warnings) == 0


def test_generate_paths_multiple_hierarchies(path_generator: PathGenerator, filter_dao: FilterDAO) -> None:
    """Test generating paths with multiple hierarchies.

    Args:
        path_generator: A test path generator.
        filter_dao: A test filter DAO.
    """
    # Register hierarchies
    artist_id = filter_dao.insert_hierarchy("AlbumArtist", 0)
    assert artist_id is not None
    album_id = filter_dao.insert_hierarchy("Album", 1)
    assert album_id is not None

    # Register values
    file_hash = "test_hash"
    assert filter_dao.insert_value(artist_id, file_hash, "Test Artist")
    assert filter_dao.insert_value(album_id, file_hash, "Test Album")

    # Generate paths
    paths = path_generator.generate_paths()
    assert len(paths) == 1

    path_info = paths[0]
    assert path_info.file_hash == file_hash
    assert path_info.relative_path == Path("Test Artist/Test Album")
    assert len(path_info.warnings) == 0


def test_generate_paths_multiple_files(path_generator: PathGenerator, filter_dao: FilterDAO) -> None:
    """Test generating paths for multiple files.

    Args:
        path_generator: A test path generator.
        filter_dao: A test filter DAO.
    """
    # Register hierarchies
    artist_id = filter_dao.insert_hierarchy("AlbumArtist", 0)
    assert artist_id is not None
    album_id = filter_dao.insert_hierarchy("Album", 1)
    assert album_id is not None

    # Register values for first file
    file_hash1 = "hash1"
    assert filter_dao.insert_value(artist_id, file_hash1, "Artist 1")
    assert filter_dao.insert_value(album_id, file_hash1, "Album 1")

    # Register values for second file
    file_hash2 = "hash2"
    assert filter_dao.insert_value(artist_id, file_hash2, "Artist 2")
    assert filter_dao.insert_value(album_id, file_hash2, "Album 2")

    # Generate paths
    paths = path_generator.generate_paths()
    assert len(paths) == 2

    # Check first path
    path1 = next(p for p in paths if p.file_hash == file_hash1)
    assert path1.relative_path == Path("Artist 1/Album 1")
    assert len(path1.warnings) == 0

    # Check second path
    path2 = next(p for p in paths if p.file_hash == file_hash2)
    assert path2.relative_path == Path("Artist 2/Album 2")
    assert len(path2.warnings) == 0


def test_generate_paths_missing_values(path_generator: PathGenerator, filter_dao: FilterDAO) -> None:
    """Test generating paths with missing values.

    Args:
        path_generator: A test path generator.
        filter_dao: A test filter DAO.
    """
    # Register hierarchies
    artist_id = filter_dao.insert_hierarchy("AlbumArtist", 0)
    assert artist_id is not None
    album_id = filter_dao.insert_hierarchy("Album", 1)
    assert album_id is not None

    # Register only artist value
    file_hash = "test_hash"
    assert filter_dao.insert_value(artist_id, file_hash, "Test Artist")

    # Generate paths
    paths = path_generator.generate_paths()
    assert len(paths) == 0  # No paths generated due to missing album value


def test_generate_paths_no_hierarchies(path_generator: PathGenerator) -> None:
    """Test generating paths with no hierarchies.

    Args:
        path_generator: A test path generator.
    """
    paths = path_generator.generate_paths()
    assert len(paths) == 0
