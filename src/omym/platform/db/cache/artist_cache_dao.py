"""Data access object for artist_cache table."""

import sqlite3
import threading
from typing import final

from omym.platform.logging.logger import logger

_DEFAULT_ARTIST_ID = "NOART"
_DEFAULT_ROMANIZATION_SOURCE = "musicbrainz"


@final
class ArtistCacheDAO:
    """Data access object for artist_cache table."""

    conn: sqlite3.Connection
    _lock: threading.Lock

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn
        self._lock = threading.Lock()

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        """Insert or update artist ID mapping.

        Args:
            artist_name: Artist name.
            artist_id: Generated artist ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            normalized_name = artist_name.strip()
            if not normalized_name:
                return False
            with self._lock:
                cursor = self.conn.cursor()
                _ = cursor.execute(
                    """
                    INSERT INTO artist_cache (artist_name, artist_id)
                    VALUES (?, ?)
                    ON CONFLICT(artist_name) DO UPDATE SET
                        artist_id = excluded.artist_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (normalized_name, artist_id.strip()),
                )
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            with self._lock:
                self.conn.rollback()
            return False

    def get_artist_id(self, artist_name: str) -> str | None:
        """Get artist ID from cache.

        Args:
            artist_name: Artist name.

        Returns:
            Artist ID if found, None otherwise.
        """
        try:
            normalized_name = artist_name.strip()
            if not normalized_name:
                return None
            with self._lock:
                cursor = self.conn.cursor()
                _ = cursor.execute(
                    """
                    SELECT artist_id 
                    FROM artist_cache 
                    WHERE LOWER(artist_name) = LOWER(?)
                    """,
                    (normalized_name,),
                )
                result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            return None

    def get_romanized_name(self, artist_name: str) -> str | None:
        """Retrieve cached romanized artist name."""

        normalized_name = artist_name.strip()
        if not normalized_name:
            return None
        try:
            with self._lock:
                cursor = self.conn.cursor()
                _ = cursor.execute(
                    """
                    SELECT romanized_name
                    FROM artist_cache
                    WHERE LOWER(artist_name) = LOWER(?)
                    """,
                    (normalized_name,),
                )
                result = cursor.fetchone()
            romanized = result[0] if result else None
            if isinstance(romanized, str) and romanized.strip():
                return romanized
            return None
        except sqlite3.Error as e:
            logger.warning("Failed to fetch romanized name for '%s': %s", normalized_name, e)
            return None

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        """Insert or update romanized artist name information."""

        normalized_name = artist_name.strip()
        normalized_romanized = romanized_name.strip()
        if not normalized_name or not normalized_romanized:
            return False

        effective_source = (source or _DEFAULT_ROMANIZATION_SOURCE).strip() or _DEFAULT_ROMANIZATION_SOURCE

        try:
            with self._lock:
                cursor = self.conn.cursor()
                _ = cursor.execute(
                    """
                    UPDATE artist_cache
                    SET romanized_name = ?,
                        romanization_source = ?,
                        romanized_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE LOWER(artist_name) = LOWER(?)
                    """,
                    (normalized_romanized, effective_source, normalized_name),
                )
                if cursor.rowcount == 0:
                    _ = cursor.execute(
                        """
                        INSERT INTO artist_cache (
                            artist_name,
                            artist_id,
                            romanized_name,
                            romanization_source,
                            romanized_at
                        )
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            normalized_name,
                            _DEFAULT_ARTIST_ID,
                            normalized_romanized,
                            effective_source,
                        ),
                    )
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.warning(
                "Failed to upsert romanized name for '%s': %s",
                normalized_name,
                e,
            )
            with self._lock:
                self.conn.rollback()
            return False

    def clear_cache(self) -> bool:
        """Clear the artist cache.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                _ = cursor.execute("DELETE FROM artist_cache")
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Failed to clear artist cache: %s", e)
            with self._lock:
                self.conn.rollback()
            return False
