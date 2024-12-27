"""Database manager for OMYM."""

import sqlite3
from pathlib import Path
from typing import Optional, Union

from omym.utils.logger import logger


class DatabaseManager:
    """Database manager for OMYM."""

    def __init__(self, db_path: Optional[Union[Path, str]] = None) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to database file. If None, use default path in project's data directory.
                   If ":memory:", use in-memory database.
        """
        if db_path == ":memory:":
            self.db_path = ":memory:"
        elif db_path is None:
            # Use default path in project's data directory
            project_root = Path(__file__).parent.parent.parent
            db_dir = project_root / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "omym.db"
        else:
            self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Connect to database and initialize schema."""
        try:
            # Ensure directory exists if using file-based database
            if self.db_path != ":memory:":
                if isinstance(self.db_path, Path):
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect with proper settings
            try:
                self.conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,  # Wait up to 30 seconds for locks
                    isolation_level="IMMEDIATE",  # Acquire write lock immediately
                )
            except sqlite3.OperationalError as e:
                if "unable to open database file" in str(e):
                    raise PermissionError(f"Unable to open database at {self.db_path}") from e
                raise

            # Enable foreign key support and proper synchronization
            if self.conn:
                self.conn.execute("PRAGMA foreign_keys = ON")
                self.conn.execute("PRAGMA synchronous = NORMAL")
                self.conn.execute("PRAGMA journal_mode = WAL")
                self.conn.execute("PRAGMA busy_timeout = 30000")  # 30 seconds in milliseconds

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
            cursor.execute(
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

            if len(existing_tables) == 7:
                logger.debug("Tables already exist, skipping schema initialization")
                return

            # Create processing_before table
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

            # Create processing_after table
            cursor.execute(
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
            cursor.execute(
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
            cursor.execute(
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
            cursor.execute(
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
            cursor.execute(
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS artist_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artist_name TEXT NOT NULL,
                    artist_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (artist_name)
                )
                """
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_albums_name_artist ON albums(album_name, album_artist)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_track_positions_file_hash ON track_positions(file_hash)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_filter_values_file_hash ON filter_values(file_hash)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_filter_values_hierarchy ON filter_values(hierarchy_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_artist_cache_name ON artist_cache(artist_name)"
            )

            self.conn.commit()
            logger.info("Successfully initialized database schema")

        except sqlite3.Error as e:
            logger.error("Failed to initialize schema: %s", e)
            if self.conn:
                self.conn.rollback()
            raise

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
        self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[object]
    ) -> None:
        """Exit context manager."""
        self.close()

    def begin_transaction(self) -> None:
        """Begin a transaction."""
        if self.conn:
            self.conn.execute("BEGIN TRANSACTION")

    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if self.conn:
            self.conn.commit()

    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if self.conn:
            self.conn.rollback()
