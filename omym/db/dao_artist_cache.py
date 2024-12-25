"""Data access object for artist_cache table."""

import sqlite3
from typing import Optional

from omym.utils.logger import logger


class ArtistCacheDAO:
    """Data access object for artist_cache table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        """Insert or update artist ID mapping.

        Args:
            artist_name: Artist name.
            artist_id: Generated artist ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO artist_cache (artist_name, artist_id)
                VALUES (?, ?)
                ON CONFLICT(artist_name) DO UPDATE SET
                    artist_id = excluded.artist_id
                """,
                (artist_name, artist_id),
            )
            return True
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return False

    def get_artist_id(self, artist_name: str) -> Optional[str]:
        """Get artist ID from cache.

        Args:
            artist_name: Artist name.

        Returns:
            Artist ID if found, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT artist_id FROM artist_cache WHERE artist_name = ?",
                (artist_name,),
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None
