"""Test database functionality."""

import sqlite3
from pathlib import Path
from collections.abc import Generator

import pytest

from omym.platform.db.db_manager import DatabaseManager


@pytest.fixture
def db_manager() -> Generator[DatabaseManager, None, None]:
    """Create a database manager with in-memory database.

    Yields:
        DatabaseManager: Database manager instance.
    """
    manager = DatabaseManager(":memory:")  # Use in-memory database for isolation
    manager.connect()
    yield manager
    manager.close()


def test_database_transaction(db_manager: DatabaseManager) -> None:
    """Test database transaction management."""
    # Begin transaction
    db_manager.begin_transaction()

    # Execute some queries
    conn = db_manager.conn
    assert conn is not None
    cursor = conn.cursor()
    _ = cursor.execute(
        """
        INSERT INTO processing_before (file_hash, file_path)
        VALUES (?, ?)
        """,
        ("test_hash_1", "/test/source/path_1"),
    )

    # Commit transaction
    db_manager.commit_transaction()

    # Verify data was inserted
    _ = cursor.execute("SELECT file_hash FROM processing_before WHERE file_path = ?", ("/test/source/path_1",))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "test_hash_1"


def test_database_rollback(db_manager: DatabaseManager) -> None:
    """Test database rollback functionality."""
    # Begin transaction
    db_manager.begin_transaction()

    # Execute some queries
    conn = db_manager.conn
    assert conn is not None
    cursor = conn.cursor()
    _ = cursor.execute(
        """
        INSERT INTO processing_before (file_hash, file_path)
        VALUES (?, ?)
        """,
        ("test_hash_2", "/test/source/path_2"),
    )

    # Rollback transaction
    db_manager.rollback_transaction()

    # Verify data was not inserted
    _ = cursor.execute("SELECT file_hash FROM processing_before WHERE file_path = ?", ("/test/source/path_2",))
    result = cursor.fetchone()
    assert result is None


def test_database_connection() -> None:
    """Test database connection."""
    # Create in-memory database
    manager = DatabaseManager(":memory:")
    manager.connect()

    try:
        # Check if connection is established
        assert manager.conn is not None
        assert isinstance(manager.conn, sqlite3.Connection)

        # Check if we can execute queries
        cursor = manager.conn.cursor()
        _ = cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 1

    finally:
        manager.close()


def test_database_error_handling() -> None:
    """Test database error handling."""
    # Try to connect with invalid path
    with pytest.raises(PermissionError):
        with DatabaseManager(Path("/invalid")):
            pass


def test_database_migration(tmp_path: Path) -> None:
    """Test database migration."""
    # Create database manager with file-based database
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)
    manager.connect()

    try:
        # Check if all required tables exist
        conn = manager.conn
        assert conn is not None, "Database connection is None"
        cursor = conn.cursor()
        _ = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
            """
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected_tables = {
            "processing_before",
            "processing_after",
            "artist_cache",
            "filter_values",
            "filter_hierarchies",
            "albums",
            "track_positions",
        }
        assert tables.issuperset(expected_tables), f"Missing tables: {expected_tables - tables}"

        # Check processing_before schema
        _ = cursor.execute("PRAGMA table_info(processing_before)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            "file_hash",
            "file_path",
            "title",
            "artist",
            "album",
            "album_artist",
            "genre",
            "year",
            "track_number",
            "total_tracks",
            "disc_number",
            "total_discs",
            "created_at",
            "updated_at",
        }
        assert columns.issuperset(expected_columns), f"Missing columns: {expected_columns - columns}"

    finally:
        manager.close()
