"""Tests for ProcessingBeforeDAO path retrieval methods."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from omym.platform.db.daos.processing_before_dao import ProcessingBeforeDAO


@pytest.fixture
def dao_with_connection() -> Iterator[tuple[ProcessingBeforeDAO, sqlite3.Connection]]:
    """Provide a DAO instance with an in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    _ = conn.execute(
        "CREATE TABLE processing_before (file_hash TEXT PRIMARY KEY, file_path TEXT NOT NULL UNIQUE)"
    )
    try:
        yield ProcessingBeforeDAO(conn), conn
    finally:
        conn.close()


def test_get_source_and_file_path_return_same_result_when_record_exists(
    dao_with_connection: tuple[ProcessingBeforeDAO, sqlite3.Connection],
) -> None:
    """Ensure both path accessors return the same path for existing records."""
    dao, conn = dao_with_connection
    file_hash = "hash-123"
    file_path = Path("/music/source.flac")
    _ = conn.execute(
        "INSERT INTO processing_before (file_hash, file_path) VALUES (?, ?)",
        (file_hash, str(file_path)),
    )

    source_path = dao.get_source_path(file_hash)
    file_path_result = dao.get_file_path(file_hash)

    assert source_path == file_path_result
    assert source_path == file_path


def test_get_source_and_file_path_return_none_when_record_missing(
    dao_with_connection: tuple[ProcessingBeforeDAO, sqlite3.Connection],
) -> None:
    """Ensure both path accessors return None when no record exists."""
    dao, _ = dao_with_connection

    assert dao.get_source_path("missing-hash") is None
    assert dao.get_file_path("missing-hash") is None


def test_get_source_and_file_path_handle_sql_error(
    dao_with_connection: tuple[ProcessingBeforeDAO, sqlite3.Connection]
) -> None:
    """Ensure both path accessors swallow database errors and return None."""
    dao, _conn = dao_with_connection
    mock_cursor: MagicMock = MagicMock(spec=sqlite3.Cursor)
    mock_cursor.execute.side_effect = sqlite3.Error("boom")
    fake_conn: MagicMock = MagicMock()
    fake_conn.cursor.return_value = mock_cursor
    dao.conn = cast(sqlite3.Connection, fake_conn)

    assert dao.get_source_path("any-hash") is None
    assert dao.get_file_path("any-hash") is None
    assert mock_cursor.execute.call_count == 2
