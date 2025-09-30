"""Use cases orchestrating restoration of processed music files."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from logging import Logger, getLogger
from pathlib import Path

from omym.features.metadata import MusicProcessor
from omym.config.settings import UNPROCESSED_DIR_NAME

from ..domain.models import (
    CollisionPolicy,
    RestorePlanItem,
    RestoreRequest,
    RestoreResult,
)
from .ports import FileSystemGateway, MaintenanceGateway, RestorePlanReader

SUPPORTED_AUDIO_EXTENSIONS = MusicProcessor.SUPPORTED_EXTENSIONS
SUPPORTED_IMAGE_EXTENSIONS = MusicProcessor.SUPPORTED_IMAGE_EXTENSIONS


@dataclass(slots=True)
class _RestoreContext:
    """Container for state required while executing a single plan item."""

    request: RestoreRequest
    plan: RestorePlanItem


class RestorationService:
    """Coordinate restore planning and execution through injected ports."""

    _plan_reader: RestorePlanReader
    _filesystem: FileSystemGateway
    _maintenance: MaintenanceGateway
    _logger: Logger

    def __init__(
        self,
        *,
        plan_reader: RestorePlanReader,
        filesystem: FileSystemGateway,
        maintenance: MaintenanceGateway,
        logger: Logger | None = None,
    ) -> None:
        self._plan_reader = plan_reader
        self._filesystem = filesystem
        self._maintenance = maintenance
        self._logger = logger or getLogger(__name__)

    def build_plan(self, request: RestoreRequest) -> list[RestorePlanItem]:
        """Construct a deterministic restore plan for ``request``."""

        candidates = self._plan_reader.fetch_restore_candidates(
            source_root=request.source_root,
            limit=request.limit,
        )
        plan: list[RestorePlanItem] = []
        for candidate in candidates:
            destination = self._resolve_destination(
                original_path=candidate.original_path,
                staged_path=candidate.staged_path,
                request=request,
            )
            plan.append(
                RestorePlanItem(
                    file_hash=candidate.file_hash,
                    source_path=candidate.staged_path,
                    destination_path=destination,
                )
            )
        plan.extend(self._build_unprocessed_plan(request))
        return plan

    def execute(self, request: RestoreRequest, plan: Iterable[RestorePlanItem]) -> list[RestoreResult]:
        """Execute ``plan`` and return per-item results."""

        results: list[RestoreResult] = []
        for item in plan:
            ctx = _RestoreContext(request=request, plan=item)
            try:
                results.append(self._execute_single(ctx))
            except Exception as exc:  # pragma: no cover - defensive logging
                message = str(exc) or exc.__class__.__name__
                self._logger.error(
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
            self._filesystem.remove_empty_directories(request.source_root)
        return results

    def run(self, request: RestoreRequest) -> list[RestoreResult]:
        """Plan and execute restoration in a single call."""

        plan = self.build_plan(request)
        return self.execute(request, plan)

    def clear_state(self) -> bool:
        """Drop cached organization state after a successful restoration."""

        return self._maintenance.clear_all()

    def _execute_single(self, ctx: _RestoreContext) -> RestoreResult:
        item = ctx.plan
        request = ctx.request
        warnings: list[str] = []

        if not self._filesystem.exists(item.source_path):
            message = "Current file not found; nothing to restore"
            self._logger.warning(
                "%s: %s",
                self._relative_source(item.source_path, request),
                message,
            )
            return RestoreResult(plan=item, moved=False, message=message)

        if self._paths_match(item.source_path, item.destination_path):
            relative_destination = self._relative_destination(
                item.destination_path,
                request,
                ctx,
            )
            self._logger.info(
                "Skipping restore because source already matches destination: %s",
                relative_destination,
            )
            return RestoreResult(
                plan=item,
                moved=False,
                message="already_restored",
            )

        if not request.dry_run:
            _ = self._filesystem.ensure_parent(item.destination_path)

        collision_result = self._handle_collision(ctx)
        if collision_result is not None:
            return collision_result

        if request.dry_run:
            self._logger.info(
                "Dry run: would move %s → %s",
                self._relative_source(item.source_path, request),
                self._relative_destination(item.destination_path, request, ctx),
            )
            warnings.append("dry_run")
            return RestoreResult(
                plan=item,
                moved=False,
                message="dry_run",
                warnings=warnings,
            )

        self._filesystem.move(item.source_path, item.destination_path)
        self._logger.info(
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

        if not self._filesystem.exists(destination):
            return None

        relative_destination = self._relative_destination(destination, request, ctx)
        message_prefix = f"Destination already exists: {relative_destination}"
        if request.collision_policy is CollisionPolicy.ABORT:
            if request.dry_run:
                self._logger.warning("%s (dry run abort)", message_prefix)
                return RestoreResult(plan=item, moved=False, message="destination_exists")
            raise FileExistsError(message_prefix)

        if request.collision_policy is CollisionPolicy.SKIP:
            self._logger.info(
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
            self._logger.info(
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

        self._filesystem.move(destination, backup_path)
        self._logger.info(
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
        candidate = destination.with_name(f"{stem}{suffix}{destination.suffix}")
        counter = 1
        while self._filesystem.exists(candidate):
            candidate = destination.with_name(f"{stem}{suffix}-{counter}{destination.suffix}")
            counter += 1
        return candidate

    def _resolve_destination(
        self,
        *,
        original_path: Path,
        staged_path: Path,
        request: RestoreRequest,
    ) -> Path:
        if request.destination_root is None:
            return original_path

        try:
            relative = staged_path.relative_to(request.source_root)
        except ValueError:
            relative = staged_path.name
        return request.destination_root / relative

    def _restore_associated_assets(self, ctx: _RestoreContext) -> list[str]:
        warnings: list[str] = []
        warnings.extend(self._restore_lyrics(ctx))
        warnings.extend(self._restore_directory_artwork(ctx))
        return warnings

    def _restore_lyrics(self, ctx: _RestoreContext) -> list[str]:
        request = ctx.request
        source_audio = ctx.plan.source_path
        destination_audio = ctx.plan.destination_path
        lyrics_source = source_audio.with_suffix(".lrc")

        warnings: list[str] = []
        if not self._filesystem.exists(lyrics_source):
            return warnings

        lyrics_target = destination_audio.with_suffix(".lrc")

        if request.dry_run:
            if self._filesystem.exists(lyrics_target):
                self._log_collision_preview(ctx, lyrics_target, request.collision_policy, "lyrics")
            self._logger.info(
                "Dry run: would move lyrics %s → %s",
                self._relative_source(lyrics_source, request),
                self._relative_destination(lyrics_target, request, ctx),
            )
            warnings.append("lyrics_dry_run")
            return warnings

        if self._filesystem.exists(lyrics_target):
            collision = self._prepare_asset_collision(ctx, lyrics_target, request, asset_label="lyrics")
            if isinstance(collision, RestoreResult):
                warnings.append("lyrics_destination_exists")
                return warnings

        _ = self._filesystem.ensure_parent(lyrics_target)
        self._filesystem.move(lyrics_source, lyrics_target)
        self._logger.info(
            "Restored lyrics %s → %s",
            self._relative_source(lyrics_source, request),
            self._relative_destination(lyrics_target, request, ctx),
        )
        return warnings

    def _restore_directory_artwork(self, ctx: _RestoreContext) -> list[str]:
        source_audio = ctx.plan.source_path
        destination_audio = ctx.plan.destination_path
        parent = source_audio.parent

        warnings: list[str] = []
        if not self._filesystem.exists(parent):
            return warnings

        entries = [entry for entry in self._filesystem.list_directory(parent) if self._filesystem.is_file(entry)]

        supported_tracks = sorted(
            entry for entry in entries if entry.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        )
        track_candidates = list(supported_tracks)
        if source_audio not in track_candidates:
            track_candidates.append(source_audio)
            track_candidates.sort()
        if not track_candidates or track_candidates[0] != source_audio:
            return warnings

        artwork_sources = sorted(
            entry for entry in entries if entry.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )
        for artwork_source in artwork_sources:
            warnings.extend(self._restore_single_artwork(ctx, artwork_source, destination_audio))
        return warnings

    def _restore_single_artwork(
        self,
        ctx: _RestoreContext,
        artwork_source: Path,
        destination_audio: Path,
    ) -> list[str]:
        request = ctx.request
        warnings: list[str] = []

        if not self._filesystem.exists(artwork_source):
            self._logger.warning(
                "Artwork source missing before restore: %s",
                self._relative_source(artwork_source, request),
            )
            warnings.append("artwork_source_missing")
            return warnings

        artwork_target = destination_audio.parent / artwork_source.name

        if self._paths_match(artwork_source, artwork_target):
            return warnings

        if request.dry_run:
            if self._filesystem.exists(artwork_target):
                self._log_collision_preview(ctx, artwork_target, request.collision_policy, "artwork")
            self._logger.info(
                "Dry run: would move artwork %s → %s",
                self._relative_source(artwork_source, request),
                self._relative_destination(artwork_target, request, ctx),
            )
            warnings.append("artwork_dry_run")
            return warnings

        if self._filesystem.exists(artwork_target):
            collision = self._prepare_asset_collision(ctx, artwork_target, request, asset_label="artwork")
            if isinstance(collision, RestoreResult):
                warnings.append("artwork_destination_exists")
                return warnings

        _ = self._filesystem.ensure_parent(artwork_target)
        self._filesystem.move(artwork_source, artwork_target)
        self._logger.info(
            "Restored artwork %s → %s",
            self._relative_source(artwork_source, request),
            self._relative_destination(artwork_target, request, ctx),
        )
        return warnings

    def _log_collision_preview(
        self,
        ctx: _RestoreContext,
        path: Path,
        policy: CollisionPolicy,
        asset_label: str,
    ) -> None:
        """Record how collisions would be handled during a dry run."""

        message = self._relative_destination(path, ctx.request, ctx)
        if policy is CollisionPolicy.ABORT:
            self._logger.warning(
                "Dry run: %s destination exists and would abort (%s)",
                asset_label,
                message,
            )
        elif policy is CollisionPolicy.BACKUP:
            backup_path = self._compute_backup_path(path, ctx.request.backup_suffix)
            self._logger.info(
                "Dry run: would rename existing %s %s → %s",
                asset_label,
                message,
                self._relative_destination(
                    backup_path,
                    ctx.request,
                    ctx,
                    original_destination=path,
                ),
            )
        else:
            self._logger.info(
                "Dry run: would skip restoring %s because destination exists: %s",
                asset_label,
                message,
            )

    def _prepare_asset_collision(
        self,
        ctx: _RestoreContext,
        destination: Path,
        request: RestoreRequest,
        *,
        asset_label: str,
    ) -> RestoreResult | None:
        """Handle collisions for non-audio assets."""

        policy = request.collision_policy
        if policy is CollisionPolicy.ABORT:
            raise FileExistsError(
                f"Destination {asset_label} already exists: {self._relative_destination(destination, request, ctx)}"
            )
        if policy is CollisionPolicy.SKIP:
            self._logger.info(
                "Skipping %s restore because destination exists: %s",
                asset_label,
                self._relative_destination(destination, request, ctx),
            )
            return RestoreResult(
                plan=ctx.plan,
                moved=False,
                message=f"{asset_label}_destination_exists",
            )

        backup_path = self._compute_backup_path(destination, request.backup_suffix)
        self._filesystem.move(destination, backup_path)
        self._logger.info(
            "Renamed existing %s %s → %s",
            asset_label,
            self._relative_destination(destination, request, ctx),
            self._relative_destination(
                backup_path,
                request,
                ctx,
                original_destination=destination,
            ),
        )
        return None

    def _paths_match(self, source: Path, destination: Path) -> bool:
        if source == destination:
            return True
        return self._filesystem.same_file(source, destination)

    def _build_unprocessed_plan(self, request: RestoreRequest) -> list[RestorePlanItem]:
        unprocessed_root = request.source_root / UNPROCESSED_DIR_NAME
        if not self._filesystem.exists(unprocessed_root):
            return []

        files = self._gather_unprocessed_files(unprocessed_root)
        plan_items: list[RestorePlanItem] = []
        for file_path in files:
            try:
                relative = file_path.relative_to(unprocessed_root)
            except ValueError:
                continue

            destination = self._resolve_unprocessed_destination(relative, request)
            plan_items.append(
                RestorePlanItem(
                    file_hash=f"unprocessed::{relative.as_posix()}",
                    source_path=file_path,
                    destination_path=destination,
                )
            )

        plan_items.sort(key=lambda item: item.source_path.as_posix())
        return plan_items

    def _gather_unprocessed_files(self, root: Path) -> list[Path]:
        pending = [root]
        files: list[Path] = []
        visited: set[Path] = set()

        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            for entry in self._filesystem.list_directory(current):
                if self._filesystem.is_file(entry):
                    files.append(entry)
                elif self._filesystem.exists(entry):
                    pending.append(entry)

        files.sort(key=lambda path: path.as_posix())
        return files

    def _resolve_unprocessed_destination(self, relative: Path, request: RestoreRequest) -> Path:
        base = request.destination_root or request.source_root
        return base / relative

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


__all__ = ["RestorationService"]
