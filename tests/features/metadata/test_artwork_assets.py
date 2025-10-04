"""
Summary: Verify artwork asset helpers integrate with filesystem ports.
Why: Ensure artwork moves rely on injected filesystem behaviour.
"""

from __future__ import annotations

from pathlib import Path

from omym.features.metadata.usecases.assets import (
    ProcessLogger,
    process_artwork,
    summarize_artwork,
)
from omym.features.metadata.usecases.processing import (
    ArtworkProcessingResult,
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


def test_process_artwork_moves_file_using_port(tmp_path: Path) -> None:
    """Artwork moves should ensure the destination directory through the port."""

    logger = DummyLogger()
    filesystem = StubFilesystem()

    track_target = tmp_path / "Library" / "Artist" / "Album" / "track.mp3"
    artwork_source = tmp_path / "cover.jpg"
    _ = artwork_source.write_bytes(b"artwork")

    results = process_artwork(
        [artwork_source],
        track_target,
        dry_run=False,
        log=logger,
        process_id="pid",
        sequence=1,
        total=1,
        source_root=tmp_path,
        target_root=tmp_path / "Library",
        filesystem=filesystem,
    )

    assert results
    result = results[0]
    assert isinstance(result, ArtworkProcessingResult)
    assert result.moved is True
    assert result.target_path.parent == track_target.parent
    assert filesystem.ensure_calls == [track_target.with_name(artwork_source.name)]
    assert summarize_artwork(results) == []
