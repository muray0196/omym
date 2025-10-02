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
from typing import Any

from pytest_mock import MockerFixture

from omym.features.metadata import TrackMetadata
from omym.features.metadata.usecases.file_runner import run_file_processing


class _StubBeforeDAO:
    """Minimal DAO stub that mimics duplicate detection bookkeeping."""

    def __init__(self, duplicate_target: Path) -> None:
        self._duplicate_target = duplicate_target
        self.insert_calls: list[tuple[str, Path]] = []

    def check_file_exists(self, file_hash: str) -> bool:
        return True

    def get_target_path(self, file_hash: str) -> Path:
        return self._duplicate_target

    def insert_file(self, file_hash: str, file_path: Path) -> bool:
        self.insert_calls.append((file_hash, file_path))
        return True


class _StubAfterDAO:
    """Minimal DAO stub that records inserts for verification."""

    def __init__(self) -> None:
        self.insert_calls: list[tuple[str, Path, Path]] = []

    def insert_file(self, file_hash: str, file_path: Path, target_path: Path) -> bool:
        self.insert_calls.append((file_hash, file_path, target_path))
        return True


class _StubPreviewDAO:
    """Preview DAO stub that keeps the interface surface minimal."""

    def get_preview(self, file_hash: str) -> Any:
        return None

    def upsert_preview(self, **_: Any) -> None:
        return None

    def delete_preview(self, file_hash: str) -> None:
        return None


class _StubArtistDAO:
    """Artist DAO stub for romanization sync."""

    def upsert_romanized_name(self, *_: Any) -> None:
        return None


class _StubArtistIdGenerator:
    """Artist ID generator stub returning deterministic identifiers."""

    def generate(self, artist: str) -> str:
        return "NEW456"


class _StubRomanization:
    """Romanization stub returning names unchanged."""

    def ensure_scheduled(self, _: str) -> None:
        return None

    def await_result(self, name: str) -> str:
        return name


class _StubProcessor:
    """Processor-like stub tailored for run_file_processing tests."""

    SUPPORTED_EXTENSIONS = {".mp3"}
    SUPPORTED_IMAGE_EXTENSIONS = {".jpg"}

    def __init__(self, *, base_path: Path, duplicate_target: Path, new_target: Path) -> None:
        self.dry_run = False
        self.base_path = base_path
        self.before_dao = _StubBeforeDAO(duplicate_target)
        self.after_dao = _StubAfterDAO()
        self.preview_dao = _StubPreviewDAO()
        self.artist_dao = _StubArtistDAO()
        self.artist_id_generator = _StubArtistIdGenerator()
        self.directory_generator = object()
        self.file_name_generator = object()
        self._romanization = _StubRomanization()
        self._new_target = new_target
        self.move_calls: list[tuple[Path, Path]] = []

    def _calculate_file_hash(self, file_path: Path) -> str:
        return "hash"

    def calculate_file_hash(self, file_path: Path) -> str:
        return "hash"

    def _generate_target_path(self, metadata: TrackMetadata, *, existing_path: Path | None = None) -> Path:
        return self._new_target

    def generate_target_path(self, metadata: TrackMetadata, *, existing_path: Path | None = None) -> Path:
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
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.replace(dest_path)
        self.move_calls.append((src_path, dest_path))

    def log_processing(
        self,
        level: int,
        event: Any,
        message: str,
        *args: object,
        **context: object,
    ) -> None:
        return None

    @property
    def romanization(self) -> _StubRomanization:
        return self._romanization


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
        "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
        return_value=metadata,
    )

    result = run_file_processing(processor, old_target)

    assert result.success is True
    assert result.skipped_duplicate is False
    assert result.target_path == new_target
    assert new_target.exists()
    assert not old_target.exists()
    assert processor.move_calls == [(old_target, new_target)]
    assert processor.before_dao.insert_calls == [("hash", old_target)]
    assert processor.after_dao.insert_calls == [("hash", old_target, new_target)]
