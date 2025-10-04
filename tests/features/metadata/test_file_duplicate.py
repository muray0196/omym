"""Summary: Exercise duplicate-handling helpers around metadata processing.
Why: Verify filesystem coordination and ID generation behave under duplicate flows."""

from __future__ import annotations

from pathlib import Path

from omym.features.metadata.usecases.processing import (
    ArtworkProcessingResult,
    LyricsProcessingResult,
    ProcessingEvent,
)
from omym.features.metadata.usecases.processing.file_context import FileProcessingContext
from omym.features.metadata.usecases.processing.file_duplicate import handle_duplicate
from omym.features.metadata.usecases.ports import (
    ArtistCachePort,
    ArtistIdGeneratorPort,
    FilesystemPort,
)


class StubArtistIdGenerator(ArtistIdGeneratorPort):
    """Return deterministic identifiers for duplicate-handling tests."""

    def __init__(self) -> None:
        self.generated: list[str | None] = []

    def generate(self, artist_name: str | None) -> str:
        self.generated.append(artist_name)
        if not artist_name:
            return "UNKNOWN"
        return artist_name.upper()[:6]


class StubFilesystem(FilesystemPort):
    """Record filesystem interactions issued by duplicate handlers."""

    def __init__(self) -> None:
        self.ensure_calls: list[Path] = []

    def ensure_parent_directory(self, path: Path) -> Path:
        self.ensure_calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.parent

    def remove_empty_directories(self, directory: Path) -> None:  # pragma: no cover - unused
        del directory


class StubArtistCache(ArtistCachePort):
    """Store artist identifiers and romanized names in-memory for tests."""

    def __init__(self) -> None:
        self.ids: dict[str, str] = {}
        self.romanized: dict[str, tuple[str, str | None]] = {}

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        self.ids[artist_name] = artist_id
        return True

    def get_artist_id(self, artist_name: str) -> str | None:
        return self.ids.get(artist_name)

    def get_romanized_name(self, artist_name: str) -> str | None:
        stored = self.romanized.get(artist_name)
        return stored[0] if stored else None

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        self.romanized[artist_name] = (romanized_name, source)
        return True

    def clear_cache(self) -> bool:
        self.ids.clear()
        self.romanized.clear()
        return True


class StubProcessor:
    """Minimal processor satisfying the hooks expected by helpers."""

    dry_run: bool
    filesystem: FilesystemPort
    artist_id_generator: ArtistIdGeneratorPort
    log_calls: list[tuple[int, ProcessingEvent, str]]

    def __init__(self, filesystem: FilesystemPort) -> None:
        self.dry_run = False
        self.filesystem = filesystem
        self.artist_id_generator = StubArtistIdGenerator()
        self.log_calls = []

    def log_processing(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *args: object,
        **context: object,
    ) -> None:
        del args, context
        self.log_calls.append((level, event, message))


def _build_context(
    tmp_path: Path,
) -> tuple[FileProcessingContext, StubProcessor, Path, StubFilesystem]:
    filesystem = StubFilesystem()
    processor = StubProcessor(filesystem)
    track_path = tmp_path / "Library" / "Artist" / "Album" / "track.mp3"
    track_path.parent.mkdir(parents=True, exist_ok=True)
    _ = track_path.write_bytes(b"music")

    ctx = FileProcessingContext(
        processor=processor,
        file_path=track_path,
        process_id="pid",
        sequence=1,
        total=1,
        source_root=tmp_path,
        target_root=tmp_path / "Library",
    )
    return ctx, processor, track_path, filesystem


def test_handle_duplicate_moves_assets_via_port(tmp_path: Path) -> None:
    """Duplicate handling should reuse the filesystem port for asset moves."""

    ctx, _processor, track_path, filesystem = _build_context(tmp_path)

    lyrics_source = tmp_path / "lyrics.lrc"
    artwork_source = tmp_path / "cover.jpg"
    _ = lyrics_source.write_text("[00:00.00]Test\n")
    _ = artwork_source.write_bytes(b"artwork")

    result = handle_duplicate(
        ctx,
        target_raw=track_path,
        associated_lyrics=lyrics_source,
        associated_artwork=[artwork_source],
    )

    assert result.success is True
    assert result.skipped_duplicate is False

    assert isinstance(result.lyrics_result, LyricsProcessingResult)
    assert result.lyrics_result.moved is True

    assert result.artwork_results
    artwork_result = result.artwork_results[0]
    assert isinstance(artwork_result, ArtworkProcessingResult)
    assert artwork_result.moved is True

    expected_target_lyrics = track_path.with_suffix(".lrc")
    expected_target_artwork = track_path.with_name(artwork_source.name)

    assert filesystem.ensure_calls == [
        expected_target_lyrics,
        expected_target_artwork,
    ]
    assert expected_target_lyrics.exists()
    assert expected_target_artwork.exists()
    assert not lyrics_source.exists()
    assert not artwork_source.exists()

