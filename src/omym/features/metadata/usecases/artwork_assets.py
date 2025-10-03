"""src/omym/features/metadata/usecases/artwork_assets.py
Where: Metadata feature usecases layer.
What: Handle movement and summarisation of artwork files for tracks.
Why: Separate artwork-specific behaviour from the core processor.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from collections.abc import Iterable

from omym.platform.filesystem import ensure_parent_directory

from .asset_logging import ProcessLogger
from .processing_types import ArtworkProcessingResult, ProcessingEvent


def process_artwork(
    artwork_paths: Iterable[Path],
    target_track_path: Path | None,
    *,
    dry_run: bool,
    log: ProcessLogger,
    process_id: str,
    sequence: int | None,
    total: int | None,
    source_root: Path,
    target_root: Path,
) -> list[ArtworkProcessingResult]:
    """Move artwork files so they follow the resolved track target."""

    results: list[ArtworkProcessingResult] = []

    for artwork_path in artwork_paths:
        if target_track_path is None:
            log(
                logging.WARNING,
                ProcessingEvent.ARTWORK_SKIP_NO_TARGET,
                "Artwork skipped: target track unavailable [id=%s, src=%s]",
                process_id,
                artwork_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=artwork_path,
                source_base_path=source_root,
                target_path=artwork_path,
                target_base_path=target_root,
                linked_track_path=None,
            )
            results.append(
                ArtworkProcessingResult(
                    source_path=artwork_path,
                    target_path=artwork_path,
                    linked_track=None,
                    moved=False,
                    dry_run=dry_run,
                    reason="no_target_track",
                )
            )
            continue

        target_artwork_path = target_track_path.with_name(artwork_path.name)

        if not artwork_path.exists():
            log(
                logging.WARNING,
                ProcessingEvent.ARTWORK_SKIP_MISSING,
                "Artwork missing before move [id=%s, src=%s]",
                process_id,
                artwork_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=artwork_path,
                source_base_path=source_root,
                target_path=target_artwork_path,
                target_base_path=target_root,
                linked_track_path=target_track_path,
                error_message="source_missing",
            )
            results.append(
                ArtworkProcessingResult(
                    source_path=artwork_path,
                    target_path=target_artwork_path,
                    linked_track=target_track_path,
                    moved=False,
                    dry_run=dry_run,
                    reason="source_missing",
                )
            )
            continue

        try:
            if target_artwork_path.exists() and target_artwork_path.samefile(artwork_path):
                log(
                    logging.INFO,
                    ProcessingEvent.ARTWORK_SKIP_ALREADY_AT_TARGET,
                    "Artwork already at target [id=%s, path=%s]",
                    process_id,
                    artwork_path,
                    process_id=process_id,
                    sequence=sequence,
                    total_files=total,
                    source_path=artwork_path,
                    source_base_path=source_root,
                    target_path=target_artwork_path,
                    target_base_path=target_root,
                    linked_track_path=target_track_path,
                )
                results.append(
                    ArtworkProcessingResult(
                        source_path=artwork_path,
                        target_path=target_artwork_path,
                        linked_track=target_track_path,
                        moved=False,
                        dry_run=dry_run,
                        reason="already_at_target",
                    )
                )
                continue
        except OSError:
            pass

        if target_artwork_path.exists():
            log(
                logging.WARNING,
                ProcessingEvent.ARTWORK_SKIP_CONFLICT,
                "Target artwork already exists [id=%s, src=%s, dest=%s]",
                process_id,
                artwork_path,
                target_artwork_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=artwork_path,
                source_base_path=source_root,
                target_path=target_artwork_path,
                target_base_path=target_root,
                linked_track_path=target_track_path,
                error_message="target_exists",
            )
            results.append(
                ArtworkProcessingResult(
                    source_path=artwork_path,
                    target_path=target_artwork_path,
                    linked_track=target_track_path,
                    moved=False,
                    dry_run=dry_run,
                    reason="target_exists",
                )
            )
            continue

        if dry_run:
            log(
                logging.INFO,
                ProcessingEvent.ARTWORK_PLAN,
                "Planned artwork move [id=%s, src=%s, dest=%s]",
                process_id,
                artwork_path,
                target_artwork_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=artwork_path,
                source_base_path=source_root,
                target_path=target_artwork_path,
                target_base_path=target_root,
                linked_track_path=target_track_path,
                dry_run=dry_run,
            )
            results.append(
                ArtworkProcessingResult(
                    source_path=artwork_path,
                    target_path=target_artwork_path,
                    linked_track=target_track_path,
                    moved=False,
                    dry_run=True,
                )
            )
            continue

        try:
            _ = ensure_parent_directory(target_artwork_path)
            _ = shutil.move(str(artwork_path), str(target_artwork_path))
        except Exception as exc:
            error_message = str(exc) if str(exc) else type(exc).__name__
            log(
                logging.ERROR,
                ProcessingEvent.ARTWORK_ERROR,
                "Error moving artwork [id=%s, src=%s, dest=%s, error=%s]",
                process_id,
                artwork_path,
                target_artwork_path,
                error_message,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=artwork_path,
                source_base_path=source_root,
                target_path=target_artwork_path,
                target_base_path=target_root,
                linked_track_path=target_track_path,
                error_message=error_message,
            )
            results.append(
                ArtworkProcessingResult(
                    source_path=artwork_path,
                    target_path=target_artwork_path,
                    linked_track=target_track_path,
                    moved=False,
                    dry_run=dry_run,
                    reason=error_message,
                )
            )
            continue

        log(
            logging.INFO,
            ProcessingEvent.ARTWORK_MOVE,
            "Artwork moved [id=%s, src=%s, dest=%s]",
            process_id,
            artwork_path,
            target_artwork_path,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=artwork_path,
            source_base_path=source_root,
            target_path=target_artwork_path,
            target_base_path=target_root,
            linked_track_path=target_track_path,
        )
        results.append(
            ArtworkProcessingResult(
                source_path=artwork_path,
                target_path=target_artwork_path,
                linked_track=target_track_path,
                moved=True,
                dry_run=False,
            )
        )

    return results


def summarize_artwork(results: Iterable[ArtworkProcessingResult]) -> list[str]:
    """Convert artwork move outcomes into user-facing warnings."""

    warnings: list[str] = []
    for result in results:
        if result.dry_run and not result.moved:
            warnings.append((f"Dry run: artwork {result.source_path.name} would move to {result.target_path.name}"))
            continue

        if not result.moved:
            reason_map = {
                "target_exists": "target already exists",
                "source_missing": "source artwork missing",
                "already_at_target": "already at destination",
                "no_target_track": "target track unavailable",
            }
            reason = result.reason or "unknown reason"
            friendly_reason = reason_map.get(reason, reason)
            warnings.append(f"Artwork file {result.source_path.name} not moved: {friendly_reason}")

    return warnings


__all__ = ["process_artwork", "summarize_artwork"]
