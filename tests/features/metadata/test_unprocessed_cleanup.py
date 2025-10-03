"""tests/features/metadata/test_unprocessed_cleanup.py
Where: Metadata feature tests.
What: Validate pending-unprocessed filtering rules for associated assets.
Why: Guard against regressions that would misclassify organised files.
"""

from pathlib import Path

from omym.features.metadata.usecases.processing_types import (
    ArtworkProcessingResult,
    LyricsProcessingResult,
    ProcessResult,
)
from omym.features.metadata.usecases.unprocessed_cleanup import (
    calculate_pending_unprocessed,
)


def test_calculate_pending_ignores_already_at_target_assets(tmp_path: Path) -> None:
    """Assets already at target should not be relocated to unprocessed."""

    source_root = tmp_path / "Library"
    audio_source = source_root / "Artist" / "Album" / "track.mp3"
    lyrics_source = audio_source.with_suffix(".lrc")
    artwork_source = audio_source.with_suffix(".jpg")

    _ = lyrics_source.parent.mkdir(parents=True)
    for path in (audio_source, lyrics_source, artwork_source):
        _ = path.touch()

    snapshot = {audio_source, lyrics_source, artwork_source}

    result = ProcessResult(
        source_path=audio_source,
        target_path=audio_source,
        success=True,
        dry_run=False,
        lyrics_result=LyricsProcessingResult(
            source_path=lyrics_source,
            target_path=lyrics_source,
            moved=False,
            dry_run=False,
            reason="already_at_target",
        ),
        artwork_results=[
            ArtworkProcessingResult(
                source_path=artwork_source,
                target_path=artwork_source,
                linked_track=audio_source,
                moved=False,
                dry_run=False,
                reason="already_at_target",
            )
        ],
    )

    pending = calculate_pending_unprocessed(snapshot, [result])

    assert pending == set()
