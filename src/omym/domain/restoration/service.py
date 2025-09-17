"""Service that plans and executes restoration of processed music files."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from omym.domain.common import remove_empty_directories
from omym.domain.restoration.models import (
    CollisionPolicy,
    RestorePlanItem,
    RestoreRequest,
    RestoreResult,
)
from omym.infra.db.daos.processing_after_dao import ProcessingAfterDAO
from omym.infra.db.daos.processing_before_dao import ProcessingBeforeDAO
from omym.infra.db.daos.maintenance_dao import MaintenanceDAO
from omym.infra.db.db_manager import DatabaseManager
from omym.infra.logger.logger import logger


@dataclass(slots=True)
class _RestoreContext:
    request: RestoreRequest
    plan: RestorePlanItem


class RestorationService:
    """High-level orchestrator for restoring previously processed files."""

    db_manager: DatabaseManager
    before_dao: ProcessingBeforeDAO
    after_dao: ProcessingAfterDAO
    maintenance_dao: MaintenanceDAO

    def __init__(self, *, db_path: Path | str | None = None) -> None:
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.connect()
        if self.db_manager.conn is None:  # pragma: no cover - defensive
            raise RuntimeError("Failed to connect to database for restoration")

        conn = self.db_manager.conn
        self.before_dao = ProcessingBeforeDAO(conn)
        self.after_dao = ProcessingAfterDAO(conn)
        self.maintenance_dao = MaintenanceDAO(conn)

    def build_plan(self, request: RestoreRequest) -> list[RestorePlanItem]:
        """Construct a deterministic plan for the requested restoration."""

        candidates = self.after_dao.fetch_restore_candidates(
            request.source_root,
            limit=request.limit,
        )
        plan: list[RestorePlanItem] = []
        for file_hash, target_path, original_path in candidates:
            destination = self._resolve_destination(original_path, target_path, request)
            plan.append(
                RestorePlanItem(
                    file_hash=file_hash,
                    source_path=target_path,
                    destination_path=destination,
                )
            )
        return plan

    def execute(self, request: RestoreRequest, plan: Iterable[RestorePlanItem]) -> list[RestoreResult]:
        """Execute a sequence of plan items and report their outcomes."""

        results: list[RestoreResult] = []
        for item in plan:
            ctx = _RestoreContext(request=request, plan=item)
            try:
                result = self._execute_single(ctx)
                results.append(result)
            except Exception as exc:  # pragma: no cover - defensive logging
                message = str(exc) or exc.__class__.__name__
                logger.error(
                    "Restore failed for %s → %s: %s",
                    self._relative_source(item.source_path, request),
                    self._relative_destination(item.destination_path, request, ctx),
                    message,
                )
                results.append(
                    RestoreResult(
                        plan=item,
                        moved=False,
                        message=message,
                    )
                )
                if not request.continue_on_error:
                    break
        if not request.dry_run:
            remove_empty_directories(request.source_root)
        return results

    def run(self, request: RestoreRequest) -> list[RestoreResult]:
        """Plan and execute restoration in a single call."""

        plan = self.build_plan(request)
        return self.execute(request, plan)

    def clear_state(self) -> bool:
        """Drop cached organization state after a successful restoration."""

        return self.maintenance_dao.clear_all()

    def _execute_single(self, ctx: _RestoreContext) -> RestoreResult:
        item = ctx.plan
        request = ctx.request
        warnings: list[str] = []

        if not item.source_path.exists():
            message = "Current file not found; nothing to restore"
            logger.warning(
                "%s: %s",
                self._relative_source(item.source_path, request),
                message,
            )
            return RestoreResult(plan=item, moved=False, message=message)

        destination_parent = item.destination_path.parent
        if not request.dry_run:
            destination_parent.mkdir(parents=True, exist_ok=True)

        collision_result = self._handle_collision(ctx)
        if collision_result is not None:
            return collision_result

        if request.dry_run:
            _ = logger.info(
                "Dry run: would move %s → %s",
                self._relative_source(item.source_path, request),
                self._relative_destination(item.destination_path, request, ctx),
            )
            return RestoreResult(
                plan=item,
                moved=False,
                message="dry_run",
                warnings=["dry_run"],
            )

        _ = shutil.move(str(item.source_path), str(item.destination_path))
        _ = logger.info(
            "Restored %s → %s",
            self._relative_source(item.source_path, request),
            self._relative_destination(item.destination_path, request, ctx),
        )
        warnings.extend(self._restore_associated_assets(ctx))
        return RestoreResult(plan=item, moved=True, warnings=warnings)

    def _handle_collision(self, ctx: _RestoreContext) -> RestoreResult | None:
        item = ctx.plan
        request = ctx.request
        destination = item.destination_path

        if not destination.exists():
            return None

        relative_destination = self._relative_destination(destination, request, ctx)
        message_prefix = f"Destination already exists: {relative_destination}"
        if request.collision_policy is CollisionPolicy.ABORT:
            if request.dry_run:
                _ = logger.warning("%s (dry run abort)", message_prefix)
                return RestoreResult(plan=item, moved=False, message="destination_exists")
            raise FileExistsError(message_prefix)

        if request.collision_policy is CollisionPolicy.SKIP:
            _ = logger.info(
                "Skipping restore because destination exists: %s",
                relative_destination,
            )
            return RestoreResult(
                plan=item,
                moved=False,
                message="destination_exists",
            )

        backup_path = self._compute_backup_path(destination, request.backup_suffix)
        if request.dry_run:
            _ = logger.info(
                "Dry run: would rename %s → %s before restore",
                relative_destination,
                self._relative_destination(
                    backup_path,
                    request,
                    ctx,
                    original_destination=destination,
                ),
            )
            return None

        _ = shutil.move(str(destination), str(backup_path))
        _ = logger.info(
            "Renamed existing file %s → %s",
            relative_destination,
            self._relative_destination(
                backup_path,
                request,
                ctx,
                original_destination=destination,
            ),
        )
        return None

    def _compute_backup_path(self, destination: Path, suffix: str) -> Path:
        stem = destination.stem
        backup_candidate = destination.with_name(f"{stem}{suffix}{destination.suffix}")
        counter = 1
        while backup_candidate.exists():
            backup_candidate = destination.with_name(
                f"{stem}{suffix}-{counter}{destination.suffix}"
            )
            counter += 1
        return backup_candidate

    def _resolve_destination(
        self,
        original_path: Path,
        target_path: Path,
        request: RestoreRequest,
    ) -> Path:
        if request.destination_root is None:
            return original_path

        try:
            relative = target_path.relative_to(request.source_root)
        except ValueError:
            relative = target_path.name
        return request.destination_root / relative

    def _restore_associated_assets(self, ctx: _RestoreContext) -> list[str]:
        """Restore sidecar files (e.g., lyrics) that accompany the audio file."""

        request = ctx.request
        source_audio = ctx.plan.source_path
        destination_audio = ctx.plan.destination_path

        lyrics_source = source_audio.with_suffix(".lrc")
        if not lyrics_source.exists():
            return []

        lyrics_target = destination_audio.with_suffix(".lrc")
        warnings: list[str] = []

        if request.dry_run:
            if lyrics_target.exists():
                if request.collision_policy is CollisionPolicy.ABORT:
                    _ = logger.warning(
                        "Dry run: lyrics destination exists and would abort (%s)",
                        self._relative_destination(lyrics_target, request, ctx),
                    )
                elif request.collision_policy is CollisionPolicy.BACKUP:
                    backup_path = self._compute_backup_path(lyrics_target, request.backup_suffix)
                    _ = logger.info(
                        "Dry run: would rename existing lyrics %s → %s",
                        self._relative_destination(lyrics_target, request, ctx),
                        self._relative_destination(
                            backup_path,
                            request,
                            ctx,
                            original_destination=lyrics_target,
                        ),
                    )
                else:
                    _ = logger.info(
                        "Dry run: would skip restoring lyrics because destination exists: %s",
                        self._relative_destination(lyrics_target, request, ctx),
                    )
            _ = logger.info(
                "Dry run: would move lyrics %s → %s",
                self._relative_source(lyrics_source, request),
                self._relative_destination(lyrics_target, request, ctx),
            )
            warnings.append("lyrics_dry_run")
            return warnings

        if lyrics_target.exists():
            if request.collision_policy is CollisionPolicy.ABORT:
                raise FileExistsError(
                    f"Destination lyrics already exists: {self._relative_destination(lyrics_target, request, ctx)}"
                )
            if request.collision_policy is CollisionPolicy.SKIP:
                _ = logger.info(
                    "Skipping lyrics restore because destination exists: %s",
                    self._relative_destination(lyrics_target, request, ctx),
                )
                warnings.append("lyrics_destination_exists")
                return warnings
            backup_path = self._compute_backup_path(lyrics_target, request.backup_suffix)
            _ = shutil.move(str(lyrics_target), str(backup_path))
            _ = logger.info(
                "Renamed existing lyrics %s → %s",
                self._relative_destination(lyrics_target, request, ctx),
                self._relative_destination(
                    backup_path,
                    request,
                    ctx,
                    original_destination=lyrics_target,
                ),
            )

        lyrics_target.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.move(str(lyrics_source), str(lyrics_target))
        _ = logger.info(
            "Restored lyrics %s → %s",
            self._relative_source(lyrics_source, request),
            self._relative_destination(lyrics_target, request, ctx),
        )
        return warnings

    def _relative_source(self, path: Path, request: RestoreRequest) -> Path | str:
        return self._relative(path, request.source_root)

    def _relative_destination(
        self,
        path: Path,
        request: RestoreRequest,
        ctx: _RestoreContext,
        *,
        original_destination: Path | None = None,
    ) -> Path | str:
        base = request.destination_root
        if base is None:
            base = (original_destination or ctx.plan.destination_path).parent
        return self._relative(path, base)

    @staticmethod
    def _relative(path: Path, base: Path) -> Path | str:
        try:
            return path.relative_to(base)
        except ValueError:
            return path
