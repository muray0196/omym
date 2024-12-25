"""Tests for the filtering engine."""

import sqlite3
from typing import Dict, Set

import pytest

from omym.core.filtering import FilterDAO, HierarchicalFilter


@pytest.fixture
def conn():
    """Create a test database connection."""
    conn = sqlite3.connect(":memory:")
    with conn:
        conn.executescript(
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
def filter_dao(conn):
    """Create a test filter DAO."""
    return FilterDAO(conn)


@pytest.fixture
def filter_engine(conn):
    """Create a test filter engine."""
    return HierarchicalFilter(conn)


def test_register_hierarchies(filter_engine):
    """Test registering filter hierarchies."""
    path_format = "AlbumArtist/Album"
    warnings = filter_engine.register_hierarchies(path_format)
    assert len(warnings) == 0


def test_process_file(filter_engine):
    """Test processing a file."""
    # Register hierarchies
    path_format = "AlbumArtist/Album"
    warnings = filter_engine.register_hierarchies(path_format)
    assert len(warnings) == 0

    # Process file
    file_hash = "test_hash"
    metadata = {
        "albumartist": "Test Artist",
        "album": "Test Album",
    }
    warnings = filter_engine.process_file(file_hash, metadata)
    assert len(warnings) == 0


def test_process_file_missing_values(filter_engine):
    """Test processing a file with missing values."""
    # Register hierarchies
    path_format = "AlbumArtist/Album"
    warnings = filter_engine.register_hierarchies(path_format)
    assert len(warnings) == 0

    # Process file with missing values
    file_hash = "test_hash"
    metadata = {
        "albumartist": "Test Artist",
        # Missing album
    }
    warnings = filter_engine.process_file(file_hash, metadata)
    assert len(warnings) == 1
    assert "Missing value for hierarchy 'Album'" in warnings[0]


def test_process_file_unknown_hierarchy(filter_engine):
    """Test processing a file with unknown hierarchy."""
    # Register hierarchies
    path_format = "Unknown"
    warnings = filter_engine.register_hierarchies(path_format)
    assert len(warnings) == 0

    # Process file with unknown hierarchy
    file_hash = "test_hash"
    metadata = {
        "unknown": "Test Value",
    }
    warnings = filter_engine.process_file(file_hash, metadata)
    assert len(warnings) == 0
