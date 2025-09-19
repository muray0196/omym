"""Tests for the restoration domain service."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from omym.domain.restoration import CollisionPolicy, RestoreRequest, RestorationService


@pytest.fixture()
def service() -> RestorationService:
    """Provide a restoration service backed by an in-memory database."""

    return RestorationService(db_path=":memory:")


def _register_sample_record(
    service: RestorationService,
    *,
    file_hash: str,
    original_path: Path,
    target_path: Path,
) -> None:
    conn = service.db_manager.conn
    assert conn is not None
    cursor = conn.cursor()
    _ = cursor.execute(
        """
        INSERT INTO processing_before (file_hash, file_path)
        VALUES (?, ?)
        ON CONFLICT(file_hash) DO UPDATE SET file_path = excluded.file_path
        """,
        (file_hash, str(original_path)),
    )
    _ = cursor.execute(
        """
        INSERT INTO processing_after (file_hash, file_path, target_path)
        VALUES (?, ?, ?)
        ON CONFLICT(file_hash) DO UPDATE SET file_path = excluded.file_path, target_path = excluded.target_path
        """,
        (file_hash, str(original_path), str(target_path)),
    )
    conn.commit()


def test_restore_moves_file(tmp_path: Path, service: RestorationService) -> None:
    """Restoration should move files back to their original location."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"dummy-audio")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    assert original_path.exists()
    assert not target_path.exists()
    assert results and results[0].moved is True


def test_restore_backup_collision(tmp_path: Path, service: RestorationService) -> None:
    """Backup policy should rename the destination when it already exists."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    _ = original_path.write_bytes(b"existing")
    backup_expected = original_dir / "song.bak.mp3"

    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"restored")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.BACKUP,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    assert original_path.exists()
    assert original_path.read_bytes() == b"restored"
    assert backup_expected.exists()
    assert backup_expected.read_bytes() == b"existing"
    assert results and results[0].moved is True


def test_restore_dry_run(tmp_path: Path, service: RestorationService) -> None:
    """Dry runs should not move files but still produce plan entries."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"restored")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=True,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    assert target_path.exists()
    assert not original_path.exists()
    assert results and results[0].moved is False
    assert results[0].message == "dry_run"


def test_restore_moves_lyrics_and_cleans_directories(tmp_path: Path, service: RestorationService) -> None:
    """Associated lyrics are restored and empty directories in source are removed."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    original_lyrics = original_path.with_suffix(".lrc")
    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"data")
    target_lyrics = target_path.with_suffix(".lrc")
    _ = target_lyrics.write_text("lyrics")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    assert results and results[0].moved is True
    assert original_path.exists()
    assert original_path.read_bytes() == b"data"
    assert original_lyrics.exists()
    assert original_lyrics.read_text() == "lyrics"
    assert not target_path.exists()
    assert not target_lyrics.exists()
    assert not organized_dir.exists()


def test_restore_moves_artwork(tmp_path: Path, service: RestorationService) -> None:
    """Artwork assets travel back with the primary restored track."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"data")
    artwork_source = target_path.parent / "cover.jpg"
    _ = artwork_source.write_bytes(b"art")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    original_artwork = original_dir / "cover.jpg"
    assert results and results[0].moved is True
    assert original_path.exists()
    assert original_path.read_bytes() == b"data"
    assert original_artwork.exists()
    assert original_artwork.read_bytes() == b"art"
    assert not artwork_source.exists()


def test_restore_artwork_collision_backup(tmp_path: Path, service: RestorationService) -> None:
    """Artwork restoration honours the configured collision policy."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"data")

    existing_artwork = original_dir / "cover.jpg"
    _ = existing_artwork.write_bytes(b"old")

    artwork_source = target_path.parent / "cover.jpg"
    _ = artwork_source.write_bytes(b"new")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.BACKUP,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    backup_artwork = original_dir / "cover.bak.jpg"
    restored_artwork = original_dir / "cover.jpg"
    assert results and results[0].moved is True
    assert restored_artwork.exists()
    assert restored_artwork.read_bytes() == b"new"
    assert backup_artwork.exists()
    assert backup_artwork.read_bytes() == b"old"
    assert not artwork_source.exists()


def test_restore_lyrics_collision_backup(tmp_path: Path, service: RestorationService) -> None:
    """Existing lyrics honour the configured collision policy."""

    original_dir = tmp_path / "original"
    organized_dir = tmp_path / "organized"
    original_dir.mkdir()
    organized_dir.mkdir()

    original_path = original_dir / "song.mp3"
    original_lyrics = original_path.with_suffix(".lrc")
    _ = original_lyrics.write_text("existing")
    target_path = organized_dir / "Artist" / "song.mp3"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _ = target_path.write_bytes(b"data")
    target_lyrics = target_path.with_suffix(".lrc")
    _ = target_lyrics.write_text("new")

    file_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=original_path,
        target_path=target_path,
    )

    request = RestoreRequest(
        source_root=organized_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.BACKUP,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    assert results and results[0].moved is True
    backup_path = original_lyrics.with_name("song.bak.lrc")
    assert backup_path.exists()
    assert backup_path.read_text() == "existing"
    assert original_lyrics.exists()
    assert original_lyrics.read_text() == "new"


def test_restore_skips_when_source_matches_destination(
    tmp_path: Path, service: RestorationService
) -> None:
    """Restoration should treat identical source and destination paths as a no-op."""

    library_dir = tmp_path / "library"
    library_dir.mkdir()
    track_path = library_dir / "song.mp3"
    _ = track_path.write_bytes(b"data")

    file_hash = hashlib.sha256(track_path.read_bytes()).hexdigest()
    _register_sample_record(
        service,
        file_hash=file_hash,
        original_path=track_path,
        target_path=track_path,
    )

    request = RestoreRequest(
        source_root=library_dir,
        destination_root=None,
        dry_run=False,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
    )

    results = service.run(request)

    assert results and results[0].moved is False
    assert results[0].message == "already_restored"
    assert track_path.exists()
    assert track_path.read_bytes() == b"data"
