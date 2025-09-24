"""Maintenance DAO for cross-table cleanup operations.

This DAO centralizes destructive maintenance actions (e.g., clearing caches
and processing state) so that higher layers (services/UI) don't issue raw SQL
directly. Keeping this logic here preserves layering and simplifies auditing.
"""

from __future__ import annotations

import sqlite3
from typing import final

from omym.platform.logging.logger import logger


@final
class MaintenanceDAO:
    """Provide cross-table maintenance operations.

    Note: Operations are best-effort and commit on success; callers may wrap
    with additional error handling depending on UX needs.
    """

    conn: sqlite3.Connection

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def clear_all(self) -> bool:
        """Clear processing state and caches in a referentially safe order.

        Order matters due to foreign keys and implied relationships.
        Returns True on success, False on failure. Errors are logged and
        transaction is rolled back on failure.
        """
        try:
            cur = self.conn.cursor()
            # Delete in FK-safe order
            _ = cur.execute("DELETE FROM processing_after")
            _ = cur.execute("DELETE FROM track_positions")
            _ = cur.execute("DELETE FROM filter_values")
            _ = cur.execute("DELETE FROM processing_before")
            _ = cur.execute("DELETE FROM albums")
            _ = cur.execute("DELETE FROM artist_cache")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Failed to clear all processing state: %s", e)
            try:
                self.conn.rollback()
            except sqlite3.Error:
                # Best-effort rollback
                pass
            return False
