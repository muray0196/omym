"""Data access object for artist ID cache."""

from sqlite3 import Connection
from typing import List, Optional, Tuple

from omym.utils.logger import logger


class ArtistCacheDAO:
    """Data access object for artist ID cache.

    This class provides methods to cache and retrieve artist IDs,
    which are used to generate consistent directory names for artists.
    """

    def __init__(self, conn: Connection):
        """Initialize DAO.

        Args:
            conn: SQLite database connection.
        """
        self.conn = conn

    def get_artist_id(self, artist_name: str) -> Optional[str]:
        """Get artist ID from cache.

        Args:
            artist_name: Artist name to look up.

        Returns:
            Optional[str]: Artist ID if found, None if not found or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT artist_id FROM artist_cache WHERE artist_name = ?",
                (artist_name,),
            )
            result = cursor.fetchone()
            return result[0] if result else None

        except Exception as e:
            if "no such table" in str(e):
                logger.debug("Artist cache table not found: %s", e)
            else:
                logger.error("Failed to get artist ID from cache: %s", e)
            return None

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        """Insert artist ID into cache.

        If the artist name already exists, updates the artist ID and
        the updated_at timestamp.

        Args:
            artist_name: Artist name to cache.
            artist_id: Generated artist ID to associate with the name.

        Returns:
            bool: True if successful, False if the operation failed.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO artist_cache (artist_name, artist_id)
                VALUES (?, ?)
                ON CONFLICT(artist_name) DO UPDATE SET
                    artist_id = excluded.artist_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (artist_name, artist_id),
            )
            self.conn.commit()
            return True

        except Exception as e:
            if "no such table" in str(e):
                logger.debug("Artist cache table not found: %s", e)
            else:
                logger.error("Failed to insert artist ID into cache: %s", e)
            self.conn.rollback()
            return False

    def get_all_artists(self) -> List[Tuple[str, str]]:
        """Get all artist mappings from cache.

        Returns:
            List[Tuple[str, str]]: List of (artist_name, artist_id) tuples.
            Returns an empty list if the table doesn't exist or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT artist_name, artist_id FROM artist_cache")
            return cursor.fetchall()

        except Exception as e:
            if "no such table" in str(e):
                logger.debug("Artist cache table not found: %s", e)
            else:
                logger.error("Failed to get all artists from cache: %s", e)
            return []
