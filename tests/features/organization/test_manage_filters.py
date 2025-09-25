"""Tests for the filtering engine."""

import sqlite3

import pytest

from omym.features.organization import HierarchicalFilter
from omym.features.organization.usecases.ports import (
    FilterHierarchyRecord,
    FilterRegistryPort,
)
from omym.platform.db.daos.filter_dao import FilterDAO


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

def test_register_hierarchies_normalizes_path_format(
    filter_engine: HierarchicalFilter,
    filter_dao: FilterDAO,
) -> None:
    """Ensure path format parsing drops empty segments and trims whitespace."""
    path_format = " AlbumArtist // Album / Year/ "

    warnings = filter_engine.register_hierarchies(path_format)

    assert warnings == []

    hierarchies = filter_dao.get_hierarchies()
    assert [hierarchy.name for hierarchy in hierarchies] == ["AlbumArtist", "Album", "Year"]
    assert [hierarchy.priority for hierarchy in hierarchies] == [0, 1, 2]


def test_filter_engine_accepts_port_injection() -> None:
    """HierarchicalFilter should rely on the provided filter port when supplied."""

    class StubFilterPort(FilterRegistryPort):
        def __init__(self) -> None:
            self.hierarchies: list[FilterHierarchyRecord] = []
            self.values: dict[int, list[tuple[str, str]]] = {}

        def insert_hierarchy(self, name: str, priority: int) -> int | None:
            identifier = len(self.hierarchies) + 1
            self.hierarchies.append(FilterHierarchyRecord(id=identifier, name=name, priority=priority))
            return identifier

        def get_hierarchies(self) -> list[FilterHierarchyRecord]:
            return list(self.hierarchies)

        def insert_value(self, hierarchy_id: int, file_hash: str, value: str) -> bool:
            self.values.setdefault(hierarchy_id, []).append((file_hash, value))
            return True

    port = StubFilterPort()
    engine = HierarchicalFilter(filter_port=port)

    assert engine.register_hierarchies("AlbumArtist/Album") == []
    warnings = engine.process_file(
        "hash",
        {
            "albumartist": "Artist",
            "album": "Album",
        },
    )

    assert warnings == []
    assert len(port.hierarchies) == 2
    assert port.values == {1: [("hash", "Artist")], 2: [("hash", "Album")]}
