"""Application service to restore previously organized music files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import final

from omym.domain.restoration import (
    CollisionPolicy,
    RestoreRequest,
    RestoreResult,
    RestorationService,
)


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
    """Application layer façade for the restoration domain service."""

    def __init__(self) -> None:
        self._service = RestorationService()

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
