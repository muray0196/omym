# /*
# Where: tests/features/metadata/test_file_runner_reorganize.py
# What: Regression coverage ensuring reorganize moves run despite cached hashes.
# Why: Guard against duplicate short-circuit blocking metadata-driven relocations.
# Assumptions:
# - Path.rename suffices to simulate file moves within the temporary filesystem.
# - MetadataExtractor provides TrackMetadata consistent with serializer expectations.
# Trade-offs:
# - Lightweight processor stub covers only the pathways needed for reorganization checks.
# */

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from omym.features.metadata.usecases.ports import (
    ArtistCachePort,
    ProcessingAfterPort,
    ProcessingBeforePort,
    PreviewCachePort,
)
from omym.features.path.usecases.renamer import (
    CachedArtistIdGenerator,
    DirectoryGenerator,
    FileNameGenerator,
)
from omym.shared import PreviewCacheEntry, TrackMetadata

from pytest_mock import MockerFixture

from omym.features.metadata.usecases.extraction.romanization import RomanizationCoordinator
from omym.features.metadata.usecases.processing.file_runner import run_file_processing


class _StubBeforeDAO(ProcessingBeforePort):
    """Minimal DAO stub that mimics duplicate detection bookkeeping."""

    _duplicate_target: Path
    insert_calls: list[tuple[str, Path]]

    def __init__(self, duplicate_target: Path) -> None:
        self._duplicate_target = duplicate_target
        self.insert_calls = []

    def check_file_exists(self, file_hash: str) -> bool:
        del file_hash
        return True

    def get_target_path(self, file_hash: str) -> Path | None:
        del file_hash
        return self._duplicate_target

    def insert_file(self, file_hash: str, file_path: Path) -> bool:
        self.insert_calls.append((file_hash, file_path))
        return True


class _StubAfterDAO(ProcessingAfterPort):
    """Minimal DAO stub that records inserts for verification."""

    insert_calls: list[tuple[str, Path, Path]]

    def __init__(self) -> None:
        self.insert_calls = []

    def insert_file(self, file_hash: str, file_path: Path, target_path: Path) -> bool:
        self.insert_calls.append((file_hash, file_path, target_path))
        return True


class _StubPreviewDAO(PreviewCachePort):
    """Preview DAO stub that keeps the interface surface minimal."""

    def get_preview(self, file_hash: str) -> PreviewCacheEntry | None:
        del file_hash
        return None

    def upsert_preview(
        self,
        *,
        file_hash: str,
        source_path: Path,
        base_path: Path,
        target_path: Path | None,
        payload: dict[str, object],
    ) -> bool:
        del file_hash
        del source_path
        del base_path
        del target_path
        del payload
        return True

    def delete_preview(self, file_hash: str) -> bool:
        del file_hash
        return True


class _StubArtistDAO(ArtistCachePort):
    """Artist DAO stub for romanization sync."""

    _ids: dict[str, str]
    _romanized: dict[str, tuple[str, str | None]]

    def __init__(self) -> None:
        self._ids = {}
        self._romanized = {}

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        self._ids[artist_name] = artist_id
        return True

    def get_artist_id(self, artist_name: str) -> str | None:
        return self._ids.get(artist_name)

    def get_romanized_name(self, artist_name: str) -> str | None:
        stored = self._romanized.get(artist_name)
        return stored[0] if stored else None

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        self._romanized[artist_name] = (romanized_name, source)
        return True

    def clear_cache(self) -> bool:
        self._ids.clear()
        self._romanized.clear()
        return True


class _StubRomanization:
    """Romanization stub returning names unchanged."""

    def ensure_scheduled(self, _: str) -> None:
        return None

    def await_result(self, name: str) -> str:
        return name


class _StubProcessor:
    """Processor-like stub tailored for run_file_processing tests."""

    SUPPORTED_EXTENSIONS: set[str] = {".mp3"}
    SUPPORTED_IMAGE_EXTENSIONS: set[str] = {".jpg"}
    dry_run: bool
    base_path: Path
    before_dao: ProcessingBeforePort
    before_dao_stub: _StubBeforeDAO
    after_dao: ProcessingAfterPort
    after_dao_stub: _StubAfterDAO
    preview_dao: PreviewCachePort
    preview_dao_stub: _StubPreviewDAO
    artist_dao: ArtistCachePort
    artist_dao_stub: _StubArtistDAO
    artist_id_generator: CachedArtistIdGenerator
    directory_generator: DirectoryGenerator
    file_name_generator: FileNameGenerator
    _romanization: _StubRomanization
    _new_target: Path
    move_calls: list[tuple[Path, Path]]

    def __init__(self, *, base_path: Path, duplicate_target: Path, new_target: Path) -> None:
        self.dry_run = False
        self.base_path = base_path
        self.before_dao_stub = _StubBeforeDAO(duplicate_target)
        self.before_dao = self.before_dao_stub
        self.after_dao_stub = _StubAfterDAO()
        self.after_dao = self.after_dao_stub
        self.preview_dao_stub = _StubPreviewDAO()
        self.preview_dao = self.preview_dao_stub
        self.artist_dao_stub = _StubArtistDAO()
        self.artist_dao = self.artist_dao_stub
        self.artist_id_generator = CachedArtistIdGenerator(self.artist_dao_stub)
        self.directory_generator = DirectoryGenerator()
        self.file_name_generator = FileNameGenerator(self.artist_id_generator)
        self._romanization = _StubRomanization()
        self._new_target = new_target
        self.move_calls = []

    def _calculate_file_hash(self, file_path: Path) -> str:
        del file_path
        return "hash"

    def calculate_file_hash(self, file_path: Path) -> str:
        del file_path
        return "hash"

    def _generate_target_path(
        self,
        metadata: TrackMetadata,
        *,
        existing_path: Path | None = None,
    ) -> Path:
        del metadata
        del existing_path
        return self._new_target

    def generate_target_path(
        self,
        metadata: TrackMetadata,
        *,
        existing_path: Path | None = None,
    ) -> Path:
        del metadata
        del existing_path
        return self._new_target

    def _move_file(
        self,
        src_path: Path,
        dest_path: Path,
        *,
        process_id: str | None = None,
        sequence: int | None = None,
        total: int | None = None,
        source_root: Path | None = None,
        target_root: Path | None = None,
    ) -> None:
        del process_id
        del sequence
        del total
        del source_root
        del target_root
        self.move_file(src_path, dest_path)

    def move_file(
        self,
        src_path: Path,
        dest_path: Path,
        *,
        process_id: str | None = None,
        sequence: int | None = None,
        total: int | None = None,
        source_root: Path | None = None,
        target_root: Path | None = None,
    ) -> None:
        del process_id
        del sequence
        del total
        del source_root
        del target_root
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        _ = src_path.replace(dest_path)
        self.move_calls.append((src_path, dest_path))

    def log_processing(
        self,
        level: int,
        event: Any,
        message: str,
        *args: object,
        **context: object,
    ) -> None:
        del level
        del event
        del message
        _ = (args, context)
        return None

    @property
    def romanization(self) -> RomanizationCoordinator:
        return cast(RomanizationCoordinator, cast(object, self._romanization))


def test_reorganize_moves_when_target_changes(tmp_path: Path, mocker: MockerFixture) -> None:
    """Relocate files when metadata-driven targets differ despite cached hashes."""

    base_path = tmp_path / "library"
    base_path.mkdir()

    old_target = base_path / "Old Artist" / "0000_Old Album" / "01_Title_OLD123.mp3"
    old_target.parent.mkdir(parents=True, exist_ok=True)
    _ = old_target.write_text("music")

    new_target = base_path / "New Artist" / "1979_New Album" / "01_Title_NEW456.mp3"

    processor = _StubProcessor(
        base_path=base_path,
        duplicate_target=old_target,
        new_target=new_target,
    )

    metadata = TrackMetadata(
        title="Title",
        artist="New Artist",
        album="New Album",
        album_artist="New Artist",
        year=1979,
        track_number=1,
        disc_number=None,
        disc_total=None,
        track_total=None,
        genre=None,
        file_extension=".mp3",
    )

    _ = mocker.patch(
        "omym.features.metadata.usecases.processing.file_runner.MetadataExtractor.extract",
        return_value=metadata,
    )

    result = run_file_processing(processor, old_target)

    assert result.success is True
    assert result.skipped_duplicate is False
    assert result.target_path == new_target
    assert new_target.exists()
    assert not old_target.exists()
    assert processor.move_calls == [(old_target, new_target)]
    assert processor.before_dao_stub.insert_calls == [("hash", old_target)]
    assert processor.after_dao_stub.insert_calls == [("hash", old_target, new_target)]
