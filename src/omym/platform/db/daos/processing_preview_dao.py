"""src/omym/platform/db/daos/processing_preview_dao.py
What: Manage cached dry-run preview records for reuse.
Why: Persist dry-run computation results so real runs can skip redundant work.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Final, cast

from omym.shared import PreviewCacheEntry
from omym.platform.logging import logger


class ProcessingPreviewDAO:
    """Data access object for the processing_preview table."""

    _UPSERT_SQL: Final[str] = (
        """
        INSERT INTO processing_preview (
            file_hash,
            source_path,
            base_path,
            target_path,
            payload_json
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(file_hash) DO UPDATE SET
            source_path = excluded.source_path,
            base_path = excluded.base_path,
            target_path = excluded.target_path,
            payload_json = excluded.payload_json,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn: sqlite3.Connection = conn

    def upsert_preview(
        self,
        *,
        file_hash: str,
        source_path: Path,
        base_path: Path,
        target_path: Path | None,
        payload: dict[str, object],
    ) -> bool:
        """Insert or update a preview entry."""

        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                self._UPSERT_SQL,
                (
                    file_hash,
                    str(source_path),
                    str(base_path),
                    str(target_path) if target_path else None,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to upsert processing preview for %s: %s", file_hash, exc)
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            return False

    def get_preview(self, file_hash: str) -> PreviewCacheEntry | None:
        """Fetch a preview entry by file hash."""

        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                """
                SELECT source_path, base_path, target_path, payload_json
                FROM processing_preview
                WHERE file_hash = ?
                """,
                (file_hash,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            source_raw, base_raw, target_raw, payload_raw = row
            payload_dict = cast(dict[str, object], json.loads(payload_raw)) if payload_raw else {}
            return PreviewCacheEntry(
                file_hash=file_hash,
                source_path=Path(source_raw),
                base_path=Path(base_raw),
                target_path=Path(target_raw) if target_raw else None,
                payload=payload_dict,
            )
        except (sqlite3.Error, json.JSONDecodeError) as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch processing preview for %s: %s", file_hash, exc)
            return None

    def delete_preview(self, file_hash: str) -> bool:
        """Remove a preview entry."""

        try:
            cursor = self.conn.cursor()
            _ = cursor.execute(
                "DELETE FROM processing_preview WHERE file_hash = ?",
                (file_hash,),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to delete processing preview for %s: %s", file_hash, exc)
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            return False

    def clear(self) -> bool:
        """Remove all preview entries."""

        try:
            cursor = self.conn.cursor()
            _ = cursor.execute("DELETE FROM processing_preview")
            self.conn.commit()
            return True
        except sqlite3.Error as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to clear processing preview table: %s", exc)
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            return False


__all__ = ["ProcessingPreviewDAO"]
