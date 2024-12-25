"""Data access object for post-processing state."""

from pathlib import Path
from sqlite3 import Connection
from typing import List, Optional, Tuple

from omym.utils.logger import logger


class ProcessingAfterDAO:
    """Data access object for post-processing state.

    This class manages the storage and retrieval of processed file information,
    tracking the mapping between original file paths and their target locations
    after processing.
    """

    def __init__(self, conn: Connection):
        """Initialize DAO.

        Args:
            conn: SQLite database connection.
        """
        self.conn = conn

    def insert_file(self, file_path: Path, file_hash: str, target_path: Path) -> bool:
        """Insert file into post-processing state.

        If a file with the same path already exists, updates its target path
        and sets the updated_at timestamp.

        Args:
            file_path: Original path to the music file.
            file_hash: Hash of the file content.
            target_path: Target path after processing.

        Returns:
            bool: True if successful, False if the operation failed.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO processing_after (file_path, file_hash, target_path)
                VALUES (:path, :hash, :target)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    target_path = excluded.target_path,
                    updated_at = CURRENT_TIMESTAMP
                """,
                {
                    "path": str(file_path),
                    "hash": file_hash,
                    "target": str(target_path),
                },
            )
            self.conn.commit()
            return True

        except Exception as e:
            logger.error("Failed to insert processed file: %s", e)
            self.conn.rollback()
            return False

    def get_target_path(self, file_path: Path) -> Optional[Path]:
        """Get target path for a processed file.

        Args:
            file_path: Original path to the music file.

        Returns:
            Optional[Path]: Target path if found, None if the file doesn't exist
                or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT target_path
                FROM processing_after
                WHERE file_path = :path
                """,
                {"path": str(file_path)},
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None

        except Exception as e:
            logger.error("Failed to get target path: %s", e)
            return None

    def get_all_files(self) -> List[Tuple[Path, str, Path]]:
        """Get all processed files.

        Returns:
            List[Tuple[Path, str, Path]]: List of (file_path, file_hash, target_path).
            Returns an empty list if no files exist or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT file_path, file_hash, target_path
                FROM processing_after
                ORDER BY file_path
                """
            )
            return [(Path(row[0]), row[1], Path(row[2])) for row in cursor.fetchall()]

        except Exception as e:
            logger.error("Failed to get all processed files: %s", e)
            return []

    def delete_file(self, file_path: Path) -> bool:
        """Delete file from post-processing state.

        Args:
            file_path: Original path to the music file.

        Returns:
            bool: True if successful, False if the file doesn't exist or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                DELETE FROM processing_after
                WHERE file_path = :path
                """,
                {"path": str(file_path)},
            )
            self.conn.commit()
            return True

        except Exception as e:
            logger.error("Failed to delete processed file: %s", e)
            self.conn.rollback()
            return False
