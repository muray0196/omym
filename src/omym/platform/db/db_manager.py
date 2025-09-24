"""Database manager for OMYM."""

import sqlite3
from pathlib import Path
from typing import final, Any

from omym.platform.filesystem import ensure_directory, ensure_parent_directory
from omym.platform.logging.logger import logger
from omym.config.paths import default_data_dir


@final
class DatabaseManager:
    """Database manager for OMYM."""

    db_path: str | Path
    conn: sqlite3.Connection | None

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to database file. If None, use default path in project's data directory.
                   If ":memory:", use in-memory database.
        """
        if db_path == ":memory:":
            self.db_path = ":memory:"
        elif db_path is None:
            # Prefer repository-root data directory, env overridable
            data_dir = default_data_dir()
            _ = ensure_directory(data_dir)
            self.db_path = data_dir / "omym.db"
        else:
            self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.conn = None

    def connect(self) -> None:
        """Connect to database and initialize schema."""
        try:
            # Ensure directory exists if using file-based database
            if self.db_path != ":memory:":
                if isinstance(self.db_path, Path):
                    _ = ensure_parent_directory(self.db_path)

            # Connect with proper settings
            try:
                self.conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,  # Wait up to 30 seconds for locks
                    isolation_level="IMMEDIATE",  # Acquire write lock immediately
                    check_same_thread=False,  # Allow DAO usage from worker threads
                )
            except sqlite3.OperationalError as e:
                if "unable to open database file" in str(e):
                    raise PermissionError(f"Unable to open database at {self.db_path}") from e
                raise

            # Enable foreign key support and proper synchronization
            if self.conn:
                _ = self.conn.execute("PRAGMA foreign_keys = ON")
                _ = self.conn.execute("PRAGMA synchronous = NORMAL")
                _ = self.conn.execute("PRAGMA journal_mode = WAL")
                _ = self.conn.execute("PRAGMA busy_timeout = 30000")  # 30 seconds in milliseconds

                # Initialize schema
                self._init_schema()

        except sqlite3.Error as e:
            logger.error("Failed to connect to database: %s", e)
            raise

    def _init_schema(self) -> None:
        """Initialize database schema."""
        if self.conn is None:
            return

        try:
            cursor = self.conn.cursor()

            # Check if tables exist
            expected_tables = {
                "processing_before",
                "processing_after",
                "artist_cache",
                "albums",
                "track_positions",
                "filter_hierarchies",
                "filter_values",
            }

            _ = cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN (
                    'processing_before',
                    'processing_after',
                    'artist_cache',
                    'albums',
                    'track_positions',
                    'filter_hierarchies',
                    'filter_values'
                )
                """
            )
            existing_tables = {row[0] for row in cursor.fetchall()}
            artist_cache_exists = "artist_cache" in existing_tables

            if existing_tables.issuperset(expected_tables):
                if artist_cache_exists:
                    self._ensure_artist_cache_columns(cursor)
                    self.conn.commit()
                logger.debug("Tables already exist, skipping schema initialization")
                return

            # Create processing_before table
            _ = cursor.execute(
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

            # Create processing_after table
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_after (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    target_path TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
                )
                """
            )

            # Create albums table
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS albums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    album_name TEXT NOT NULL,
                    album_artist TEXT NOT NULL,
                    year INTEGER,
                    total_tracks INTEGER,
                    total_discs INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (album_name, album_artist)
                )
                """
            )

            # Create track_positions table
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS track_positions (
                    album_id INTEGER NOT NULL,
                    disc_number INTEGER NOT NULL,
                    track_number INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (album_id, disc_number, track_number),
                    FOREIGN KEY (album_id) REFERENCES albums (id),
                    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
                )
                """
            )

            # Create filter_hierarchies table
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS filter_hierarchies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (name)
                )
                """
            )

            # Create filter_values table
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS filter_values (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hierarchy_id INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (hierarchy_id) REFERENCES filter_hierarchies (id),
                    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
                )
                """
            )

            # Create artist_cache table
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS artist_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artist_name TEXT NOT NULL,
                    artist_id TEXT NOT NULL,
                    romanized_name TEXT,
                    romanization_source TEXT,
                    romanized_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (artist_name)
                )
                """
            )

            # Create indexes for better performance
            _ = cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_name_artist ON albums(album_name, album_artist)")
            _ = cursor.execute("CREATE INDEX IF NOT EXISTS idx_track_positions_file_hash ON track_positions(file_hash)")
            _ = cursor.execute("CREATE INDEX IF NOT EXISTS idx_filter_values_file_hash ON filter_values(file_hash)")
            _ = cursor.execute("CREATE INDEX IF NOT EXISTS idx_filter_values_hierarchy ON filter_values(hierarchy_id)")
            _ = cursor.execute("CREATE INDEX IF NOT EXISTS idx_artist_cache_name ON artist_cache(artist_name)")

            self._ensure_artist_cache_columns(cursor)
            self.conn.commit()
            logger.info("Successfully initialized database schema")

        except sqlite3.Error as e:
            logger.error("Failed to initialize schema: %s", e)
            if self.conn:
                self.conn.rollback()
            raise

    def _ensure_artist_cache_columns(self, cursor: sqlite3.Cursor) -> None:
        """Ensure legacy databases include romanization columns."""

        _ = cursor.execute("PRAGMA table_info(artist_cache)")
        columns = {row[1] for row in cursor.fetchall()}

        if "romanized_name" not in columns:
            _ = cursor.execute("ALTER TABLE artist_cache ADD COLUMN romanized_name TEXT")
        if "romanization_source" not in columns:
            _ = cursor.execute("ALTER TABLE artist_cache ADD COLUMN romanization_source TEXT")
        if "romanized_at" not in columns:
            _ = cursor.execute("ALTER TABLE artist_cache ADD COLUMN romanized_at DATETIME")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
            except sqlite3.Error as e:
                logger.error("Failed to close database connection: %s", e)

    def __enter__(self) -> "DatabaseManager":
        """Enter context manager."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Exit context manager."""
        self.close()

    def begin_transaction(self) -> None:
        """Begin a transaction."""
        if self.conn:
            _ = self.conn.execute("BEGIN TRANSACTION")

    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if self.conn:
            self.conn.commit()

    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if self.conn:
            self.conn.rollback()
