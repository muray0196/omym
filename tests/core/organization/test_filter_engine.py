"""Tests for the filtering engine."""

import sqlite3

import pytest

from omym.domain.organization.filter_engine import HierarchicalFilter
from omym.infra.db.daos.filter_dao import FilterDAO


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
            CREATE TABLE filter_hierarchies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (name)
            );

            CREATE TABLE filter_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hierarchy_id INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hierarchy_id) REFERENCES filter_hierarchies (id)
            );
            """
        )
    return conn


@pytest.fixture
def filter_dao(conn: sqlite3.Connection) -> FilterDAO:
    """Create a test filter DAO.

    Args:
        conn: SQLite database connection.

    Returns:
        FilterDAO: Filter DAO instance.
    """
    return FilterDAO(conn)


@pytest.fixture
def filter_engine(conn: sqlite3.Connection) -> HierarchicalFilter:
    """Create a test filter engine.

    Args:
        conn: SQLite database connection.

    Returns:
        HierarchicalFilter: Filter engine instance.
    """
    return HierarchicalFilter(conn)


def test_register_hierarchies(filter_engine: HierarchicalFilter) -> None:
    """Test registering filter hierarchies."""
    path_format = "AlbumArtist/Album"
    warnings = filter_engine.register_hierarchies(path_format)
    assert isinstance(warnings, list)
    assert len(warnings) == 0


def test_process_file(filter_engine: HierarchicalFilter) -> None:
    """Test processing a file."""
    # Register hierarchies
    path_format = "AlbumArtist/Album"
    warnings = filter_engine.register_hierarchies(path_format)
    assert isinstance(warnings, list)
    assert len(warnings) == 0

    # Process file
    file_hash = "test_hash"
    metadata: dict[str, str | None] = {
        "albumartist": "Test Artist",
        "album": "Test Album",
    }
    warnings = filter_engine.process_file(file_hash, metadata)
    assert isinstance(warnings, list)
    assert len(warnings) == 0


def test_process_file_missing_values(filter_engine: HierarchicalFilter) -> None:
    """Test processing a file with missing values."""
    # Register hierarchies
    path_format = "AlbumArtist/Album"
    warnings = filter_engine.register_hierarchies(path_format)
    assert isinstance(warnings, list)
    assert len(warnings) == 0

    # Process file with missing values
    file_hash = "test_hash"
    metadata: dict[str, str | None] = {
        "albumartist": "Test Artist",
        # Missing album
    }
    warnings = filter_engine.process_file(file_hash, metadata)
    assert isinstance(warnings, list)
    assert len(warnings) == 1
    assert "Missing value for hierarchy 'Album'" in warnings[0]


def test_process_file_unknown_hierarchy(filter_engine: HierarchicalFilter) -> None:
    """Test processing a file with unknown hierarchy."""
    # Register hierarchies
    path_format = "Unknown"
    warnings = filter_engine.register_hierarchies(path_format)
    assert isinstance(warnings, list)
    assert len(warnings) == 0

    # Process file with unknown hierarchy
    file_hash = "test_hash"
    metadata: dict[str, str | None] = {
        "unknown": "Test Value",
    }
    warnings = filter_engine.process_file(file_hash, metadata)
    assert isinstance(warnings, list)
    assert len(warnings) == 0
