"""Tests for database functionality."""

import sqlite3
from pathlib import Path
from typing import Generator

import pytest

from omym.db.db_manager import DatabaseManager


@pytest.fixture
def db_manager() -> Generator[DatabaseManager, None, None]:
    """Create a database manager with in-memory database.

    Yields:
        DatabaseManager: Database manager instance.
    """
    with DatabaseManager() as manager:
        yield manager


def test_database_transaction(db_manager: DatabaseManager) -> None:
    """Test database transaction management."""
    # Begin transaction
    db_manager.begin_transaction()

    # Execute some queries
    conn = db_manager.conn
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO processing_before (file_hash, file_path)
        VALUES (?, ?)
        """,
        ("test_hash", "test_path"),
    )

    # Commit transaction
    db_manager.commit_transaction()

    # Verify data was saved
    cursor.execute(
        """
        SELECT file_hash, file_path
        FROM processing_before
        WHERE file_hash = ?
        """,
        ("test_hash",),
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "test_hash"
    assert row[1] == "test_path"


def test_database_rollback(db_manager: DatabaseManager) -> None:
    """Test database rollback."""
    # Begin transaction
    db_manager.begin_transaction()

    # Execute some queries
    conn = db_manager.conn
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO processing_before (file_hash, file_path)
        VALUES (?, ?)
        """,
        ("test_hash", "test_path"),
    )

    # Rollback transaction
    db_manager.rollback_transaction()

    # Verify data was not saved
    cursor.execute(
        """
        SELECT file_hash, file_path
        FROM processing_before
        WHERE file_hash = ?
        """,
        ("test_hash",),
    )
    row = cursor.fetchone()
    assert row is None


def test_database_connection(tmp_path: Path) -> None:
    """Test database connection with file path."""
    db_path = tmp_path / "test.db"

    # First connection: create table and insert data
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_before (
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
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO processing_before (file_hash, file_path)
            VALUES (?, ?)
            """,
            ("test_hash", "test_path"),
        )
        conn.commit()

    # Verify file exists
    assert db_path.exists()

    # Second connection: verify data
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Ensure the table exists
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='processing_before'
            """
        )
        assert cursor.fetchone() is not None, "Table not found"

        # Query the data
        cursor.execute(
            """
            SELECT file_hash, file_path
            FROM processing_before
            WHERE file_hash = ?
            """,
            ("test_hash",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test_hash"
        assert row[1] == "test_path"

    # Now test with DatabaseManager
    with DatabaseManager(db_path) as manager:
        conn = manager.conn
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_hash, file_path
            FROM processing_before
            WHERE file_hash = ?
            """,
            ("test_hash",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test_hash"
        assert row[1] == "test_path"


def test_database_error_handling() -> None:
    """Test database error handling."""
    # Try to connect with invalid path
    with pytest.raises(sqlite3.OperationalError):
        with DatabaseManager(Path("/invalid/path/db.sqlite")):
            pass

    # Try to execute invalid SQL
    with pytest.raises(sqlite3.OperationalError):
        with DatabaseManager() as manager:
            conn = manager.conn
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("INVALID SQL")


def test_database_migration(tmp_path: Path) -> None:
    """Test database migration."""
    db_path = tmp_path / "test.db"
    with DatabaseManager(db_path) as manager:
        # Verify tables exist
        conn = manager.conn
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "albums" in tables
        assert "filter_hierarchies" in tables
        assert "filter_values" in tables
        assert "processing_after" in tables
        assert "processing_before" in tables
        assert "track_positions" in tables
