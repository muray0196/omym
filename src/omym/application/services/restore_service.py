"""Application service to restore previously organized music files."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger, getLogger
from pathlib import Path
from typing import final

from omym.features.restoration import (
    CollisionPolicy,
    RestorationService,
    RestoreRequest,
    RestoreResult,
)
from omym.features.restoration.adapters.db.sqlite_repository import SqliteRestoreRepository
from omym.features.restoration.adapters.filesystem.local import LocalFileSystemGateway
from omym.features.restoration.usecases.ports import (
    FileSystemGateway,
    MaintenanceGateway,
    RestorePlanReader,
)
from omym.platform.db.db_manager import DatabaseManager


@dataclass(slots=True)
class RestoreServiceRequest:
    """Parameters describing a restoration run."""

    source_root: Path
    destination_root: Path | None = None
    dry_run: bool = False
    collision_policy: CollisionPolicy = CollisionPolicy.ABORT
    backup_suffix: str = ".bak"
    continue_on_error: bool = False
    limit: int | None = None
    purge_state: bool = False


@final
class RestoreMusicService:
    """Application façade wiring adapters into the restoration use case."""

    _service: RestorationService
    _plan_reader: RestorePlanReader
    _maintenance: MaintenanceGateway
    _filesystem: FileSystemGateway

    def __init__(
        self,
        *,
        db_path: Path | str | None = None,
        plan_reader: RestorePlanReader | None = None,
        maintenance: MaintenanceGateway | None = None,
        filesystem: FileSystemGateway | None = None,
        logger: Logger | None = None,
    ) -> None:
        if (plan_reader is None) != (maintenance is None):
            raise ValueError("plan_reader and maintenance must be provided together")

        if plan_reader is None:
            manager = DatabaseManager(db_path)
            sqlite_repository = SqliteRestoreRepository(manager)
            self._plan_reader = sqlite_repository
            self._maintenance = sqlite_repository
        else:
            assert maintenance is not None
            self._plan_reader = plan_reader
            self._maintenance = maintenance

        fs_gateway = filesystem or LocalFileSystemGateway()
        service_logger = logger or getLogger(__name__)

        self._filesystem = fs_gateway
        self._service = RestorationService(
            plan_reader=self._plan_reader,
            filesystem=self._filesystem,
            maintenance=self._maintenance,
            logger=service_logger,
        )

    def run(self, request: RestoreServiceRequest) -> list[RestoreResult]:
        """Execute restoration and optionally purge persistent state."""

        domain_request = RestoreRequest(
            source_root=request.source_root,
            destination_root=request.destination_root,
            dry_run=request.dry_run,
            collision_policy=request.collision_policy,
            backup_suffix=request.backup_suffix,
            continue_on_error=request.continue_on_error,
            limit=request.limit,
        )
        plan = self._service.build_plan(domain_request)
        results = self._service.execute(domain_request, plan)

        if request.purge_state and not request.dry_run:
            _ = self._service.clear_state()

        return results
