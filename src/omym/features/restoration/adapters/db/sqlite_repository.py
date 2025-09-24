"""SQLite-backed adapters for the restoration feature."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omym.platform.db.daos.maintenance_dao import MaintenanceDAO
from omym.platform.db.daos.processing_after_dao import ProcessingAfterDAO
from omym.platform.db.db_manager import DatabaseManager

from ...usecases.ports import MaintenanceGateway, RestoreCandidate, RestorePlanReader


@dataclass(slots=True)
class SqliteRestoreRepository(RestorePlanReader, MaintenanceGateway):
    """Bridge restoration use cases to the SQLite persistence layer."""

    _db_manager: DatabaseManager
    _after_dao: ProcessingAfterDAO
    _maintenance_dao: MaintenanceDAO

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db_manager = db_manager
        if self._db_manager.conn is None:
            self._db_manager.connect()
        if self._db_manager.conn is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Database connection could not be established")

        conn = self._db_manager.conn
        self._after_dao = ProcessingAfterDAO(conn)
        self._maintenance_dao = MaintenanceDAO(conn)

    def fetch_restore_candidates(
        self,
        *,
        source_root: Path | None,
        limit: int | None = None,
    ) -> list[RestoreCandidate]:
        rows = self._after_dao.fetch_restore_candidates(base_path=source_root, limit=limit)
        return [
            RestoreCandidate(
                file_hash=file_hash,
                staged_path=staged_path,
                original_path=original_path,
            )
            for file_hash, staged_path, original_path in rows
        ]

    def clear_all(self) -> bool:
        return self._maintenance_dao.clear_all()
