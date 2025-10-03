"""src/omym/features/metadata/usecases/file_management/file_success.py
What: Finalise successful processing of a track file.
Why: Keep the main runner lean by extracting post-move handling.
"""

from __future__ import annotations

import logging
from pathlib import Path

from omym.shared.track_metadata import TrackMetadata
from ..assets.associated_assets import process_artwork, process_lyrics, summarize_artwork, summarize_lyrics
from ..processing.processing_types import ProcessResult, ProcessingEvent
from .file_context import FileProcessingContext


def complete_success(
    ctx: FileProcessingContext,
    *,
    target_path: Path,
    metadata: TrackMetadata,
    associated_lyrics: Path | None,
    associated_artwork: list[Path],
    duration_ms: float,
) -> ProcessResult:
    """Produce the success result and perform asset follow-up."""

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
        )
        ctx.artwork_results.extend(artwork_plan)
        ctx.warnings.extend(summarize_artwork(artwork_plan))

    ctx.processor.log_processing(
        logging.INFO,
        ProcessingEvent.FILE_SUCCESS,
        "File processed [id=%s, name=%s, target=%s, duration_ms=%.2f]",
        ctx.process_id,
        ctx.file_path.name,
        target_path,
        duration_ms,
        process_id=ctx.process_id,
        sequence=ctx.sequence,
        total_files=ctx.total,
        source_path=ctx.file_path,
        source_base_path=ctx.source_root,
        target_path=target_path,
        target_base_path=ctx.target_root,
        file_hash=ctx.file_hash,
        duration_ms=duration_ms,
        artist=metadata.artist,
        album=metadata.album,
        title=metadata.title,
        dry_run=ctx.processor.dry_run,
    )

    artist_id: str | None = None
    if metadata.artist:
        # Reuse the cached generator so preview tables align with persisted IDs.
        generated_id = ctx.processor.artist_id_generator.generate(metadata.artist)
        artist_id = generated_id.strip() or None

    return ProcessResult(
        source_path=ctx.file_path,
        target_path=target_path,
        success=True,
        dry_run=ctx.processor.dry_run,
        file_hash=ctx.file_hash,
        metadata=metadata,
        artist_id=artist_id,
        lyrics_result=ctx.lyrics_result,
        artwork_results=ctx.artwork_results,
        warnings=ctx.warnings,
    )


__all__ = ["complete_success"]
