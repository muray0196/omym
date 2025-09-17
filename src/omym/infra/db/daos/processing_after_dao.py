"""Data access object for processing_after table."""

import os
import sqlite3
from pathlib import Path
from typing import Any, final

from omym.infra.logger.logger import logger


@final
class ProcessingAfterDAO:
    """Data access object for processing_after table."""

    conn: sqlite3.Connection

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def insert_file(self, file_hash: str, file_path: Path, target_path: Path) -> bool:
        """Insert a file record.

        Args:
            file_hash: File hash.
            file_path: Original file path.
            target_path: Target file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                INSERT INTO processing_after (
                    file_hash,
                    file_path,
                    target_path
                ) VALUES (?, ?, ?)
                ON CONFLICT(file_hash) DO UPDATE SET
                    file_path = excluded.file_path,
                    target_path = excluded.target_path,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (file_hash, str(file_path), str(target_path)),
            )
            return True
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

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
                "SELECT target_path FROM processing_after WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            return Path(result[0]) if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None

    def fetch_restore_candidates(
        self,
        base_path: Path | None = None,
        *,
        limit: int | None = None,
    ) -> list[tuple[str, Path, Path]]:
        """Return tuples of ``(file_hash, target_path, original_path)`` for restore runs.

        Args:
            base_path: Optional path prefix to filter targets below a specific directory.
            limit: Optional maximum number of records to stream.

        Returns:
            List of tuples containing the file hash, current target path, and original source path.
        """

        try:
            cursor = self.conn.cursor()
            query = (
                """
                SELECT pa.file_hash, pa.target_path, pb.file_path
                FROM processing_after pa
                INNER JOIN processing_before pb ON pb.file_hash = pa.file_hash
                {where_clause}
                ORDER BY pa.updated_at ASC
                {limit_clause}
                """
            )

            where_clause = ""
            limit_clause = ""
            params: list[Any] = []

            if base_path is not None:
                target_prefix = str(base_path.resolve())
                separator = os.sep
                if not target_prefix.endswith(separator):
                    target_prefix = f"{target_prefix}{separator}"
                where_clause = "WHERE pa.target_path LIKE ?"
                params.append(f"{target_prefix}%")

            if limit is not None:
                limit_clause = "LIMIT ?"
                params.append(limit)

            formatted_query = query.format(where_clause=where_clause, limit_clause=limit_clause)
            _ = cursor.execute(formatted_query, params)
            rows = cursor.fetchall()
            return [
                (str(file_hash), Path(target_path), Path(original_path))
                for file_hash, target_path, original_path in rows
            ]
        except sqlite3.Error as e:
            logger.error("Database error while iterating restore candidates: %s", e)
            return []
