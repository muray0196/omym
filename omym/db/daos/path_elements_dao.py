"""Data access object for path components."""

from typing import List, Optional
from sqlite3 import Connection

from omym.core.path.path_elements import ComponentValue
from omym.utils.logger import logger


class PathComponentDAO:
    """Data access object for path components."""

    def __init__(self, conn: Connection):
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def insert_component(self, file_hash: str, component: ComponentValue) -> bool:
        """Insert a path component.

        Args:
            file_hash: Hash of the file.
            component: Component value to insert.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO path_components (
                    file_hash, component_type, component_value, component_order
                ) VALUES (?, ?, ?, ?)
                """,
                (file_hash, component.type, component.value, component.order),
            )
            return True

        except Exception as e:
            logger.error("Failed to insert path component: %s", e)
            return False

    def get_components(self, file_hash: str) -> List[ComponentValue]:
        """Get all path components for a file.

        Args:
            file_hash: Hash of the file.

        Returns:
            List[ComponentValue]: List of component values.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT component_type, component_value, component_order
                FROM path_components
                WHERE file_hash = ?
                ORDER BY component_order
                """,
                (file_hash,),
            )
            return [
                ComponentValue(
                    type=row[0],
                    value=row[1],
                    order=row[2],
                )
                for row in cursor.fetchall()
            ]

        except Exception as e:
            logger.error("Failed to get path components: %s", e)
            return []

    def get_component_by_type(
        self, file_hash: str, component_type: str
    ) -> Optional[ComponentValue]:
        """Get a specific component for a file.

        Args:
            file_hash: Hash of the file.
            component_type: Type of component to get.

        Returns:
            Optional[ComponentValue]: Component value if found.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT component_value, component_order
                FROM path_components
                WHERE file_hash = ? AND component_type = ?
                """,
                (file_hash, component_type),
            )
            row = cursor.fetchone()
            if row:
                return ComponentValue(
                    value=row[0],
                    order=row[1],
                    type=component_type,
                )
            return None

        except Exception as e:
            logger.error("Failed to get path component: %s", e)
            return None

    def get_files_by_component(
        self, component_type: str, component_value: str
    ) -> List[str]:
        """Get all files that have a specific component value.

        Args:
            component_type: Type of component to match.
            component_value: Value to match.

        Returns:
            List[str]: List of file hashes.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT file_hash
                FROM path_components
                WHERE component_type = ? AND component_value = ?
                """,
                (component_type, component_value),
            )
            return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error("Failed to get files by component: %s", e)
            return []
