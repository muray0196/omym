"""Database manager for OMYM."""

import sqlite3
from pathlib import Path
from importlib import resources
from typing import Optional, Any

from omym.utils.logger import logger


class DatabaseManager:
    """Database manager for OMYM."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager.

        Args:
            db_path: Path to database file. If None, use in-memory database.
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Connect to database."""
        try:
            if self.db_path:
                self.conn = sqlite3.connect(self.db_path)
            else:
                self.conn = sqlite3.connect(":memory:")

            # Enable foreign key support and proper synchronization
            if self.conn:
                self.conn.execute("PRAGMA foreign_keys = ON")
                self.conn.execute("PRAGMA synchronous = FULL")
                self.conn.execute("PRAGMA journal_mode = WAL")

            self._init_schema()

        except Exception as e:
            logger.error("Failed to connect to database: %s", e)
            raise

    def _init_schema(self) -> None:
        """Initialize database schema."""
        try:
            if not self.conn:
                return

            # Check if tables already exist
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='processing_before'
                """
            )
            if cursor.fetchone() is not None:
                logger.debug("Tables already exist, skipping schema initialization")
                return

            # Read migration scripts
            migration_scripts = [
                resources.files("omym.db.migrations")
                .joinpath("001_initial.sql")
                .read_text(encoding="utf-8"),
            ]

            # Execute migrations
            for script in migration_scripts:
                self.conn.executescript(script)
            self.conn.commit()  # Commit the schema changes
            logger.debug("Schema initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize database schema: %s", e)
            if self.conn:
                self.conn.rollback()
            raise

    def close(self) -> None:
        """Close database connection."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None

        except Exception as e:
            logger.error("Failed to close database connection: %s", e)
            raise

    def __enter__(self) -> "DatabaseManager":
        """Enter context manager.

        Returns:
            DatabaseManager: The database manager instance.
        """
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit context manager.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        try:
            if self.conn:
                if exc_type is None:
                    try:
                        # No exception occurred, commit any pending changes
                        self.conn.commit()
                        logger.debug("Changes committed on context exit")
                    except Exception as e:
                        logger.error("Failed to commit changes: %s", e)
                        self.conn.rollback()
                        raise
                else:
                    # An exception occurred, rollback any changes
                    try:
                        self.conn.rollback()
                        logger.debug("Changes rolled back on context exit")
                    except Exception as e:
                        logger.error("Failed to rollback changes: %s", e)
                        raise
        finally:
            self.close()

    def begin_transaction(self) -> None:
        """Begin transaction."""
        try:
            if self.conn:
                self.conn.execute("BEGIN")
                logger.debug("Transaction started")

        except Exception as e:
            logger.error("Failed to begin transaction: %s", e)
            raise

    def commit_transaction(self) -> None:
        """Commit transaction."""
        try:
            if self.conn:
                self.conn.commit()
                logger.debug("Transaction committed successfully")

        except Exception as e:
            logger.error("Failed to commit transaction: %s", e)
            if self.conn:
                self.conn.rollback()
            raise

    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        try:
            if self.conn:
                self.conn.rollback()
                logger.debug("Transaction rolled back successfully")

        except Exception as e:
            logger.error("Failed to rollback transaction: %s", e)
            raise
