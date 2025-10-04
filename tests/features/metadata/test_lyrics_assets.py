"""
Summary: Exercise lyrics asset helpers and filesystem port integration.
Why: Ensure lyrics moves rely on injected filesystem behavior.
"""

from __future__ import annotations

from pathlib import Path

from omym.features.metadata.usecases.assets import (
    ProcessLogger,
    process_lyrics,
    summarize_lyrics,
)
from omym.features.metadata.usecases.processing import (
    LyricsProcessingResult,
    ProcessingEvent,
)


class StubFilesystem:
    """Track filesystem interactions for assertions."""

    def __init__(self) -> None:
        self.ensure_calls: list[Path] = []

    def ensure_parent_directory(self, path: Path) -> Path:
        self.ensure_calls.append(path)
        _ = path.parent.mkdir(parents=True, exist_ok=True)
        return path.parent

    def remove_empty_directories(self, directory: Path) -> None:  # pragma: no cover - unused
        del directory


class DummyLogger(ProcessLogger):
    """Capture structured log calls for assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, ProcessingEvent, str]] = []

    def __call__(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: object,
    ) -> None:
        del message_args, context
        self.calls.append((level, event, message))


def test_process_lyrics_missing_source(tmp_path: Path) -> None:
    """Missing lyrics should yield a descriptive result and warning."""

    logger = DummyLogger()
    audio_target = tmp_path / "Album" / "track.mp3"
    lyrics_source = tmp_path / "track.lrc"

    filesystem = StubFilesystem()

    result = process_lyrics(
        lyrics_source,
        audio_target,
        dry_run=False,
        log=logger,
        process_id="pid",
        sequence=1,
        total=1,
        source_root=tmp_path,
        target_root=tmp_path,
        filesystem=filesystem,
    )

    assert result.moved is False
    assert result.reason == "lyrics_source_missing"
    assert summarize_lyrics(result) == [
        f"Lyrics file {lyrics_source.name} not moved: source lyrics missing"
    ]
    assert any(event == ProcessingEvent.LYRICS_ERROR for _, event, _ in logger.calls)


def test_summarize_lyrics_dry_run(tmp_path: Path) -> None:
    """Dry-run behaviour should surface the planned destination."""

    planned = LyricsProcessingResult(
        source_path=tmp_path / "song.lrc",
        target_path=tmp_path / "library" / "song.lrc",
        moved=False,
        dry_run=True,
    )

    warnings = summarize_lyrics(planned)

    assert warnings == [
        "Dry run: lyrics song.lrc would move to song.lrc"
    ]


def test_process_lyrics_already_at_target(tmp_path: Path) -> None:
    """Lyrics already at the destination should be treated as organised."""

    logger = DummyLogger()
    library_root = tmp_path / "Library"
    audio_target = library_root / "Artist" / "Album" / "track.mp3"
    lyrics_source = audio_target.with_suffix(".lrc")
    _ = lyrics_source.parent.mkdir(parents=True)
    _ = lyrics_source.touch()

    filesystem = StubFilesystem()

    result = process_lyrics(
        lyrics_source,
        audio_target,
        dry_run=False,
        log=logger,
        process_id="pid",
        sequence=1,
        total=1,
        source_root=tmp_path,
        target_root=library_root,
        filesystem=filesystem,
    )

    assert result.moved is False
    assert result.reason == "already_at_target"
    assert summarize_lyrics(result) == [
        f"Lyrics file {lyrics_source.name} not moved: already organized"
    ]
    assert any(
        event is ProcessingEvent.LYRICS_SKIP_ALREADY_AT_TARGET
        for _, event, _ in logger.calls
    )


def test_process_lyrics_invokes_filesystem_port(tmp_path: Path) -> None:
    """Successful lyrics moves must ensure the destination via the filesystem port."""

    logger = DummyLogger()
    filesystem = StubFilesystem()
    audio_target = tmp_path / "Library" / "Artist" / "Album" / "track.mp3"
    lyrics_source = tmp_path / "track.lrc"
    _ = lyrics_source.write_text("[00:00.00]Hello world\n")

    result = process_lyrics(
        lyrics_source,
        audio_target,
        dry_run=False,
        log=logger,
        process_id="pid",
        sequence=1,
        total=1,
        source_root=tmp_path,
        target_root=tmp_path / "Library",
        filesystem=filesystem,
    )

    assert result.moved is True
    assert filesystem.ensure_calls == [audio_target.with_suffix(".lrc")]

