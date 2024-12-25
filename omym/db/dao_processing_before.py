"""Data access object for processing_before table."""

import sqlite3
from pathlib import Path
from typing import Optional

from omym.utils.logger import logger


class ProcessingBeforeDAO:
    """Data access object for processing_before table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def check_file_exists(self, file_hash: str) -> bool:
        """Check if a file with the given hash exists.

        Args:
            file_hash: File hash to check.

        Returns:
            True if file exists, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM processing_before WHERE file_hash = ?",
                (file_hash,),
            )
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

    def insert_file(self, file_hash: str, source_path: Path, target_path: Path) -> bool:
        """Insert a file record.

        Args:
            file_hash: File hash.
            source_path: Source file path.
            target_path: Target file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO processing_before (
                    file_hash,
                    file_path
                ) VALUES (?, ?)
                """,
                (file_hash, str(source_path)),
            )
            return True
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

    def get_source_path(self, file_hash: str) -> Optional[Path]:
        """Get source path for a file.

        Args:
            file_hash: File hash.

        Returns:
            Source path if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT file_path FROM processing_before WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None

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
                """
                SELECT pa.target_path
                FROM processing_before pb
                JOIN processing_after pa ON pb.file_hash = pa.file_hash
                WHERE pb.file_hash = ?
                """,
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None

    def get_file_path(self, file_hash: str) -> Optional[Path]:
        """Get file path for a file.

        Args:
            file_hash: File hash.

        Returns:
            File path if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT file_path FROM processing_before WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None
