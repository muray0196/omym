"""
Summary: Handle duplicate detection branch for file processing.
Why: Keep the main runner concise by isolating duplicate logic.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..assets import process_artwork, process_lyrics, summarize_artwork, summarize_lyrics
from .file_context import FileProcessingContext
from .processing_types import ProcessResult, ProcessingEvent


def handle_duplicate(
    ctx: FileProcessingContext,
    *,
    target_raw: Path | str | None,
    associated_lyrics: Path | None,
    associated_artwork: list[Path],
) -> ProcessResult:
    """Produce a duplicate result and schedule associated asset moves."""

    if isinstance(target_raw, Path):
        target_path = target_raw
    elif target_raw:
        target_path = Path(target_raw)
    else:
        target_path = None

    same_location = False

    if target_path and target_path.exists():
        try:
            same_location = target_path.samefile(ctx.file_path)
        except (FileNotFoundError, OSError):
            same_location = target_path.resolve() == ctx.file_path.resolve()

        if associated_lyrics is not None:
            ctx.lyrics_result = process_lyrics(
                associated_lyrics,
                target_path,
                dry_run=ctx.processor.dry_run,
                log=ctx.processor.log_processing,
                process_id=ctx.process_id,
                sequence=ctx.sequence,
                total=ctx.total,
                source_root=ctx.source_root,
                target_root=ctx.target_root,
                filesystem=ctx.filesystem,
            )
            ctx.warnings.extend(summarize_lyrics(ctx.lyrics_result))
        if associated_artwork:
            artwork_plan = process_artwork(
                associated_artwork,
                target_path,
                dry_run=ctx.processor.dry_run,
                log=ctx.processor.log_processing,
                process_id=ctx.process_id,
                sequence=ctx.sequence,
                total=ctx.total,
                source_root=ctx.source_root,
                target_root=ctx.target_root,
                filesystem=ctx.filesystem,
            )
            ctx.artwork_results.extend(artwork_plan)
            ctx.warnings.extend(summarize_artwork(artwork_plan))
    elif associated_artwork:
        artwork_plan = process_artwork(
            associated_artwork,
            None,
            dry_run=ctx.processor.dry_run,
            log=ctx.processor.log_processing,
            process_id=ctx.process_id,
            sequence=ctx.sequence,
            total=ctx.total,
            source_root=ctx.source_root,
            target_root=ctx.target_root,
            filesystem=ctx.filesystem,
        )
        ctx.artwork_results.extend(artwork_plan)
        ctx.warnings.extend(summarize_artwork(artwork_plan))

    target_display: Path | str | None = target_path or "<unknown>"
    event = ProcessingEvent.FILE_SKIP_DUPLICATE
    message = "File already processed [id=%s, name=%s, target=%s]"
    skipped_duplicate = True

    if same_location:
        event = ProcessingEvent.FILE_ALREADY_ORGANIZED
        message = "File already organized at target location [id=%s, name=%s, target=%s]"
        skipped_duplicate = False

    ctx.processor.log_processing(
        logging.INFO,
        event,
        message,
        ctx.process_id,
        ctx.file_path.name,
        target_display,
        process_id=ctx.process_id,
        sequence=ctx.sequence,
        total_files=ctx.total,
        source_path=ctx.file_path,
        source_base_path=ctx.source_root,
        target_path=target_path,
        target_base_path=ctx.target_root,
        file_hash=ctx.file_hash,
    )
    return ProcessResult(
        source_path=ctx.file_path,
        target_path=target_path,
        success=True,
        dry_run=ctx.processor.dry_run,
        file_hash=ctx.file_hash,
        lyrics_result=ctx.lyrics_result,
        artwork_results=ctx.artwork_results,
        warnings=ctx.warnings,
        skipped_duplicate=skipped_duplicate,
    )


__all__ = ["handle_duplicate"]
