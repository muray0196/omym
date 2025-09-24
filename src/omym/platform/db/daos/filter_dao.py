"""Data access object for filter management."""

from dataclasses import dataclass
from sqlite3 import Connection
from typing import final

from omym.platform.logging.logger import logger


@dataclass
class FilterHierarchy:
    """Filter hierarchy information."""

    id: int
    name: str
    priority: int


@dataclass
class FilterValue:
    """Filter value information."""

    hierarchy_id: int
    file_hash: str
    value: str


@final
class FilterDAO:
    """Data access object for filter management."""

    conn: Connection

    def __init__(self, conn: Connection):
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def insert_hierarchy(self, name: str, priority: int) -> int | None:
        """Insert a filter hierarchy.

        Args:
            name: Hierarchy name.
            priority: Priority value.

        Returns:
            int | None: Hierarchy ID if successful, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                INSERT INTO filter_hierarchies (name, priority)
                VALUES (?, ?)
                """,
                (name, priority),
            )
            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error("Failed to insert hierarchy: %s", e)
            self.conn.rollback()
            return None

    def get_hierarchies(self) -> list[FilterHierarchy]:
        """Get all filter hierarchies.

        Returns:
            list[FilterHierarchy]: List of filter hierarchies.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                SELECT id, name, priority
                FROM filter_hierarchies
                ORDER BY priority
                """
            )
            return [
                FilterHierarchy(
                    id=row[0],
                    name=row[1],
                    priority=row[2],
                )
                for row in cursor.fetchall()
            ]

        except Exception as e:
            logger.error("Failed to get hierarchies: %s", e)
            return []

    def insert_value(self, hierarchy_id: int, file_hash: str, value: str) -> bool:
        """Insert a filter value.

        Args:
            hierarchy_id: ID of the hierarchy.
            file_hash: Hash of the file.
            value: Filter value.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                INSERT INTO filter_values (hierarchy_id, file_hash, value)
                VALUES (?, ?, ?)
                """,
                (hierarchy_id, file_hash, value),
            )
            self.conn.commit()
            return True

        except Exception as e:
            logger.error("Failed to insert filter value: %s", e)
            self.conn.rollback()
            return False

    def get_values(self, hierarchy_id: int) -> list[FilterValue]:
        """Get all values for a hierarchy.

        Args:
            hierarchy_id: ID of the hierarchy.

        Returns:
            list[FilterValue]: List of filter values.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                SELECT file_hash, value
                FROM filter_values
                WHERE hierarchy_id = ?
                ORDER BY value
                """,
                (hierarchy_id,),
            )
            return [
                FilterValue(
                    hierarchy_id=hierarchy_id,
                    file_hash=row[0],
                    value=row[1],
                )
                for row in cursor.fetchall()
            ]

        except Exception as e:
            logger.error("Failed to get filter values: %s", e)
            return []

    def get_file_value(self, hierarchy_id: int, file_hash: str) -> str | None:
        """Get value for a specific file and hierarchy.

        Args:
            hierarchy_id: ID of the hierarchy.
            file_hash: Hash of the file.

        Returns:
            str | None: Filter value if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                SELECT value
                FROM filter_values
                WHERE hierarchy_id = ? AND file_hash = ?
                """,
                (hierarchy_id, file_hash),
            )
            result = cursor.fetchone()
            return result[0] if result else None

        except Exception as e:
            logger.error("Failed to get file value: %s", e)
            return None
