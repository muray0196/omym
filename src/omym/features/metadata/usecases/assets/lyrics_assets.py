"""src/omym/features/metadata/usecases/assets/lyrics_assets.py
Where: Metadata feature usecases layer.
What: Handle movement and summarisation of lyrics files tied to tracks.
Why: Keep lyrics-specific side effects isolated from core processing logic.
Assumptions:
- Filesystem exposes pathlib.samefile for already-organised detection.
Trade-offs:
- Treating identical source/target as organised skips warning about stale files.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from omym.platform.filesystem import ensure_parent_directory

from .asset_logging import ProcessLogger
from ..processing.processing_types import LyricsProcessingResult, ProcessingEvent


def process_lyrics(
    lyrics_path: Path,
    target_file_path: Path,
    *,
    dry_run: bool,
    log: ProcessLogger,
    process_id: str,
    sequence: int | None,
    total: int | None,
    source_root: Path,
    target_root: Path,
) -> LyricsProcessingResult:
    """Move a lyrics file so that it matches the target music file path."""

    target_lyrics_path = target_file_path.with_suffix(".lrc")

    if not lyrics_path.exists():
        log(
            logging.WARNING,
            ProcessingEvent.LYRICS_ERROR,
            "Lyrics file missing before move [id=%s, src=%s]",
            process_id,
            lyrics_path,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=lyrics_path,
            source_base_path=source_root,
            target_path=target_lyrics_path,
            target_base_path=target_root,
            error_message="lyrics_source_missing",
        )
        return LyricsProcessingResult(
            source_path=lyrics_path,
            target_path=target_lyrics_path,
            moved=False,
            dry_run=dry_run,
            reason="lyrics_source_missing",
        )

    try:
        if target_lyrics_path.exists() and target_lyrics_path.samefile(lyrics_path):
            log(
                logging.INFO,
                ProcessingEvent.LYRICS_SKIP_ALREADY_AT_TARGET,
                "Lyrics already at target [id=%s, path=%s]",
                process_id,
                lyrics_path,
                process_id=process_id,
                sequence=sequence,
                total_files=total,
                source_path=lyrics_path,
                source_base_path=source_root,
                target_path=target_lyrics_path,
                target_base_path=target_root,
            )
            return LyricsProcessingResult(
                source_path=lyrics_path,
                target_path=target_lyrics_path,
                moved=False,
                dry_run=dry_run,
                reason="already_at_target",
            )
    except OSError:
        pass

    if target_lyrics_path.exists():
        log(
            logging.WARNING,
            ProcessingEvent.LYRICS_SKIP_CONFLICT,
            "Target lyrics already exists [id=%s, src=%s, dest=%s]",
            process_id,
            lyrics_path,
            target_lyrics_path,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=lyrics_path,
            source_base_path=source_root,
            target_path=target_lyrics_path,
            target_base_path=target_root,
            error_message="target_exists",
        )
        return LyricsProcessingResult(
            source_path=lyrics_path,
            target_path=target_lyrics_path,
            moved=False,
            dry_run=dry_run,
            reason="target_exists",
        )

    if dry_run:
        log(
            logging.INFO,
            ProcessingEvent.LYRICS_PLAN,
            "Planned lyrics move [id=%s, src=%s, dest=%s]",
            process_id,
            lyrics_path,
            target_lyrics_path,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=lyrics_path,
            source_base_path=source_root,
            target_path=target_lyrics_path,
            target_base_path=target_root,
            dry_run=dry_run,
        )
        return LyricsProcessingResult(
            source_path=lyrics_path,
            target_path=target_lyrics_path,
            moved=False,
            dry_run=True,
        )

    try:
        _ = ensure_parent_directory(target_lyrics_path)
        _ = shutil.move(str(lyrics_path), str(target_lyrics_path))
    except Exception as exc:  # pragma: no cover - defensive logging
        error_message = str(exc) if str(exc) else type(exc).__name__
        log(
            logging.ERROR,
            ProcessingEvent.LYRICS_ERROR,
            "Error moving lyrics file [id=%s, src=%s, dest=%s, error=%s]",
            process_id,
            lyrics_path,
            target_lyrics_path,
            error_message,
            process_id=process_id,
            sequence=sequence,
            total_files=total,
            source_path=lyrics_path,
            source_base_path=source_root,
            target_path=target_lyrics_path,
            target_base_path=target_root,
            error_message=error_message,
        )
        return LyricsProcessingResult(
            source_path=lyrics_path,
            target_path=target_lyrics_path,
            moved=False,
            dry_run=False,
            reason=error_message,
        )

    log(
        logging.INFO,
        ProcessingEvent.LYRICS_MOVE,
        "Lyrics file moved [id=%s, src=%s, dest=%s]",
        process_id,
        lyrics_path,
        target_lyrics_path,
        process_id=process_id,
        sequence=sequence,
        total_files=total,
        source_path=lyrics_path,
        source_base_path=source_root,
        target_path=target_lyrics_path,
        target_base_path=target_root,
    )
    return LyricsProcessingResult(
        source_path=lyrics_path,
        target_path=target_lyrics_path,
        moved=True,
        dry_run=False,
    )


def summarize_lyrics(result: LyricsProcessingResult | None) -> list[str]:
    """Convert a lyrics move outcome into user-facing warnings."""

    if result is None:
        return []

    if result.dry_run and not result.moved:
        return [
            (
                "Dry run: lyrics "
                f"{result.source_path.name} would move to {result.target_path.name}"
            )
        ]

    if not result.moved:
        reason_map = {
            "target_exists": "target already exists",
            "lyrics_source_missing": "source lyrics missing",
            "already_at_target": "already organized",
        }
        reason = result.reason or "unknown reason"
        friendly_reason = reason_map.get(reason, reason)
        return [
            f"Lyrics file {result.source_path.name} not moved: {friendly_reason}"
        ]

    return []


__all__ = ["process_lyrics", "summarize_lyrics"]
