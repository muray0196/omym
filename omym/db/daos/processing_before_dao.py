"""Data access object for processing_before table."""

import sqlite3
from pathlib import Path
from typing import final

from omym.utils.logger import logger


@final
class ProcessingBeforeDAO:
    """Data access object for processing_before table."""

    conn: sqlite3.Connection

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def check_file_exists(self, file_hash: str) -> bool:
        """Check if a file with the given hash exists and is in the correct location.

        Args:
            file_hash: File hash to check.

        Returns:
            True if file exists and is in the correct location, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            # Check if file exists in processing_before and has a matching entry in processing_after
            _ = cursor.execute(
                """
                SELECT pa.target_path
                FROM processing_before pb
                LEFT JOIN processing_after pa ON pb.file_hash = pa.file_hash
                WHERE pb.file_hash = ?
                """,
                (file_hash,),
            )
            result = cursor.fetchone()

            if not result:
                return False

            target_path = result[0]

            # If there's no target path in processing_after, file needs to be processed
            if target_path is None:
                return False

            # Check if the file exists at the target path
            target_path_obj = Path(target_path)
            if not target_path_obj.exists():
                return False

            return True

        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

    def insert_file(self, file_hash: str, file_path: Path) -> bool:
        """Insert a file record.

        Args:
            file_hash: File hash.
            file_path: Source file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                INSERT INTO processing_before (
                    file_hash,
                    file_path
                ) VALUES (?, ?)
                ON CONFLICT(file_hash) DO UPDATE SET
                    file_path = excluded.file_path,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (file_hash, str(file_path)),
            )
            return True
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

    def get_source_path(self, file_hash: str) -> Path | None:
        """Get source path for a file.

        Args:
            file_hash: File hash.

        Returns:
            Source path if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                "SELECT file_path FROM processing_before WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None

    def get_target_path(self, file_hash: str) -> Path | None:
        """Get target path for a file.

        Args:
            file_hash: File hash.

        Returns:
            Target path if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
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

    def get_file_path(self, file_hash: str) -> Path | None:
        """Get file path for a file.

        Args:
            file_hash: File hash.

        Returns:
            File path if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                "SELECT file_path FROM processing_before WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None
