"""Data access object for processing_after table."""

import sqlite3
from pathlib import Path
from typing import Optional

from omym.utils.logger import logger


class ProcessingAfterDAO:
    """Data access object for processing_after table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def insert_file(self, file_hash: str, target_path: Path) -> bool:
        """Insert a file record.

        Args:
            file_hash: File hash.
            target_path: Target file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO processing_after (file_hash, target_path)
                VALUES (?, ?)
                """,
                (file_hash, str(target_path)),
            )
            return True
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

    def get_target_path(self, file_hash: str) -> Optional[Path]:
        """Get target path for a file.

        Args:
            file_hash: File hash.

        Returns:
            Target path if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT target_path FROM processing_after WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None
