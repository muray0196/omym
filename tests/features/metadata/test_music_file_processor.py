"""Tests for music file processing functionality."""

import logging
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from omym.features.metadata import TrackMetadata
from omym.config.settings import UNPROCESSED_DIR_NAME
from omym.features.metadata import (
    DirectoryRollbackError,
    MusicProcessor,
    ProcessingEvent,
    ProcessResult,
)
from omym.features.metadata.usecases.ports import PreviewCacheEntry


@pytest.fixture
def metadata() -> TrackMetadata:
    """Create a test metadata object.

    Returns:
        TrackMetadata: A test metadata object.
    """
    return TrackMetadata(
        title="Comfortably Numb",
        artist="Pink Floyd",
        album="The Wall",
        album_artist="Pink Floyd",
        year=1979,
        track_number=6,
        track_total=None,
        disc_number=2,
        disc_total=None,
        file_extension=".mp3",
    )


@pytest.fixture
def file_hash() -> str:
    """Create a test file hash.

    Returns:
        str: A test file hash.
    """
    return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
def processor(mocker: MockerFixture, tmp_path: Path, file_hash: str) -> MusicProcessor:
    """Create a test processor with mocked dependencies.

    Args:
        mocker: Pytest mocker fixture.
        tmp_path: Temporary path fixture.
        file_hash: Deterministic hash used for mocked calculations.

    Returns:
        MusicProcessor: A test processor.
    """
    # Mock database manager
    mock_db = mocker.patch("omym.features.metadata.usecases.music_file_processor.DatabaseManager").return_value
    mock_db.conn = mocker.MagicMock()

    # Mock DAOs
    mock_before_dao = mocker.patch("omym.features.metadata.usecases.music_file_processor.ProcessingBeforeDAO").return_value
    mock_after_dao = mocker.patch("omym.features.metadata.usecases.music_file_processor.ProcessingAfterDAO").return_value
    mock_artist_dao = mocker.patch("omym.features.metadata.usecases.music_file_processor.ArtistCacheDAO").return_value
    mock_preview_dao = mocker.patch("omym.features.metadata.usecases.music_file_processor.ProcessingPreviewDAO").return_value

    # Configure DAO behavior
    _ = mock_before_dao.check_file_exists.return_value = False
    _ = mock_before_dao.insert_file.return_value = True
    _ = mock_after_dao.insert_file.return_value = True
    _ = mock_artist_dao.get_artist_id.return_value = "PNKFL"
    _ = mock_artist_dao.get_romanized_name.return_value = None
    _ = mock_artist_dao.insert_artist_id.return_value = True
    _ = mock_artist_dao.upsert_romanized_name.return_value = True
    _ = mock_preview_dao.get_preview.return_value = None
    _ = mock_preview_dao.upsert_preview.return_value = True
    _ = mock_preview_dao.delete_preview.return_value = True

    # Create processor
    processor = MusicProcessor(base_path=tmp_path)

    # Mock file hash calculation
    _ = mocker.patch.object(processor, "_calculate_file_hash", return_value=file_hash)

    return processor


class TestMusicProcessor:
    """Test cases for MusicProcessor."""

    def test_process_file_success(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test successful processing of a single music file."""

        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()
        lyrics_file = tmp_path / "test.lrc"
        _ = lyrics_file.write_text("[00:00.00]Hello world\n")

        # Mock metadata extraction
        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.target_path is not None
        assert result.target_path.exists()
        assert not source_file.exists()  # Original file should be moved

        lyrics_target = result.target_path.with_suffix(".lrc")
        assert lyrics_target.exists()
        assert result.lyrics_result is not None
        assert result.lyrics_result.moved is True
        assert result.lyrics_result.target_path == lyrics_target
        assert not lyrics_file.exists()  # Lyrics should follow the audio file
        assert result.artwork_results == []
        assert result.warnings == []  # Original file should be moved

    def test_process_file_preserves_existing_name(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
    ) -> None:
        """Reprocessing a file already in place must not add a numeric suffix."""

        destination_dir = processor.base_path / processor.directory_generator.generate(metadata)
        destination_dir.mkdir(parents=True, exist_ok=True)
        file_name = processor.file_name_generator.generate(metadata)
        source_file = destination_dir / file_name
        _ = source_file.write_bytes(b"audio")

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        result = processor.process_file(source_file)

        assert result.success is True
        assert result.target_path == source_file
        assert source_file.exists()
        assert "(1)" not in source_file.name
        assert all("(1)" not in candidate.name for candidate in destination_dir.iterdir())

    def test_process_file_moves_artwork(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Artwork files follow the primary track when processing a single file."""

        source_file = tmp_path / "song.mp3"
        source_file.touch()
        artwork_file = tmp_path / "cover.jpg"
        _ = artwork_file.write_bytes(b"artwork")

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        result = processor.process_file(source_file)

        assert result.success is True
        assert result.target_path is not None
        assert len(result.artwork_results) == 1

        artwork_result = result.artwork_results[0]
        assert artwork_result.moved is True
        assert artwork_result.target_path.parent == result.target_path.parent
        assert not artwork_file.exists()
        assert artwork_result.target_path.exists()
        assert result.warnings == []

    def test_dry_run_caches_preview(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
        file_hash: str,
    ) -> None:
        """Dry-run processing should persist preview details for reuse."""

        processor.dry_run = True
        preview_mock = cast(MagicMock, processor.preview_dao)
        preview_mock.reset_mock()

        source_file = tmp_path / "dryrun.mp3"
        source_file.touch()

        metadata_copy = TrackMetadata(**asdict(metadata))
        original_artist = metadata_copy.artist
        original_album_artist = metadata_copy.album_artist

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata_copy,
        )
        processor.romanization.ensure_scheduled = MagicMock()
        def _romanize(name: str) -> str:
            return f"{name}_rn"

        processor.romanization.await_result = MagicMock(side_effect=_romanize)

        result = processor.process_file(source_file)

        assert result.dry_run is True
        preview_mock.upsert_preview.assert_called_once()
        _, kwargs = preview_mock.upsert_preview.call_args
        assert kwargs["file_hash"] == file_hash
        assert kwargs["source_path"] == source_file.resolve()
        assert kwargs["base_path"] == processor.base_path.resolve()
        payload = kwargs["payload"]
        assert payload["original_artist"] == (original_artist or "")
        assert payload["original_album_artist"] == (original_album_artist or "")
        cached_metadata = payload["metadata"]
        assert cached_metadata["artist"] == f"{original_artist}_rn"

    def test_process_file_reuses_preview_entry(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
        file_hash: str,
    ) -> None:
        """Real runs should reuse cached dry-run previews when hashes align."""

        source_file = tmp_path / "reuse.mp3"
        source_file.touch()

        preview_metadata = TrackMetadata(
            title=metadata.title,
            artist="Pink Floyd RN",
            album=metadata.album,
            album_artist="Pink Floyd RN",
            genre=metadata.genre,
            year=metadata.year,
            track_number=metadata.track_number,
            track_total=metadata.track_total,
            disc_number=metadata.disc_number,
            disc_total=metadata.disc_total,
            file_extension=metadata.file_extension,
        )
        metadata_payload = cast(object, asdict(preview_metadata))
        payload: dict[str, object] = {
            "metadata": metadata_payload,
            "original_artist": "ピンク・フロイド",
            "original_album_artist": "ピンク・フロイド",
        }
        preview_mock = cast(MagicMock, processor.preview_dao)
        preview_mock.get_preview.return_value = PreviewCacheEntry(
            file_hash=file_hash,
            source_path=source_file,
            base_path=processor.base_path,
            target_path=None,
            payload=payload,
        )

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            side_effect=AssertionError("Extraction should be skipped when preview exists"),
        )

        result = processor.process_file(source_file)

        assert result.success is True
        artist_cache_mock = cast(MagicMock, processor.artist_dao)
        artist_cache_mock.upsert_romanized_name.assert_any_call(
            "ピンク・フロイド",
            "Pink Floyd RN",
        )
        preview_mock.delete_preview.assert_called_once_with(file_hash)

    def test_process_file_artwork_conflict(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Artwork files remain when the destination already contains an image."""

        source_file = tmp_path / "song.mp3"
        source_file.touch()
        artwork_file = tmp_path / "cover.png"
        _ = artwork_file.write_bytes(b"artwork")

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        target_path = processor._generate_target_path(  # pyright: ignore[reportPrivateUsage] - tests compute the destination for collision priming
            metadata,
            existing_path=source_file,
        )
        assert target_path is not None
        conflict_target = target_path.parent / artwork_file.name
        conflict_target.parent.mkdir(parents=True, exist_ok=True)
        _ = conflict_target.write_bytes(b"existing")

        result = processor.process_file(source_file)

        assert result.success is True
        assert len(result.artwork_results) == 1
        artwork_result = result.artwork_results[0]
        assert artwork_result.moved is False
        assert artwork_result.reason == "target_exists"
        assert artwork_file.exists()
        assert conflict_target.read_bytes() == b"existing"
        assert (
            f"Artwork file {artwork_file.name} not moved: target already exists" in result.warnings
        )

    def test_process_file_duplicate_moves_artwork(
        self,
        processor: MusicProcessor,
        tmp_path: Path,
    ) -> None:
        """Duplicate detection still relocates artwork alongside the stored track."""

        source_file = tmp_path / "song.mp3"
        source_file.touch()
        artwork_file = tmp_path / "cover.jpg"
        _ = artwork_file.write_bytes(b"artwork")

        target_path = tmp_path / "library" / "song.mp3"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()

        before_dao_mock = cast(MagicMock, processor.before_dao)
        before_dao_mock.check_file_exists.return_value = True
        before_dao_mock.get_target_path.return_value = str(target_path)

        result = processor.process_file(source_file)

        assert result.skipped_duplicate is True
        assert len(result.artwork_results) == 1

        artwork_result = result.artwork_results[0]
        assert artwork_result.moved is True
        assert artwork_result.target_path.parent == target_path.parent
        assert not artwork_file.exists()
        assert artwork_result.target_path.exists()

    def test_process_file_lyrics_conflict(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Lyrics file should remain in place when the target already exists."""

        source_file = tmp_path / "track.mp3"
        source_file.touch()
        lyrics_file = tmp_path / "track.lrc"
        _ = lyrics_file.write_text("[00:00.00]Existing\n")

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        target_path = processor._generate_target_path(  # pyright: ignore[reportPrivateUsage] - tests may consult the helper to stage collision scenarios
            metadata,
            existing_path=source_file,
        )
        assert target_path is not None
        lyrics_target = target_path.with_suffix(".lrc")
        lyrics_target.parent.mkdir(parents=True, exist_ok=True)
        _ = lyrics_target.write_text("[00:00.00]Conflict\n")

        result = processor.process_file(source_file)

        assert result.success is True
        assert result.lyrics_result is not None
        assert result.lyrics_result.moved is False
        assert result.lyrics_result.reason == "target_exists"
        assert lyrics_file.exists()  # Lyrics should stay at the source due to conflict
        assert lyrics_target.read_text() == "[00:00.00]Conflict\n"
        assert (
            f"Lyrics file {lyrics_file.name} not moved: target already exists" in result.warnings
        )

    def test_process_file_metadata_error(
        self, mocker: MockerFixture, processor: MusicProcessor, tmp_path: Path
    ) -> None:
        """Test handling of metadata extraction error.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()

        # Mock metadata extraction to fail
        _ = mocker.patch("omym.features.metadata.usecases.file_runner.MetadataExtractor.extract", return_value=None)

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is False
        assert "Failed to extract metadata" in str(result.error_message)
        assert source_file.exists()  # Original file should not be moved

    def test_process_file_dry_run(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test dry run mode."""

        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()
        lyrics_file = tmp_path / "test.lrc"
        _ = lyrics_file.write_text("[00:00.00]Preview\n")
        processor.dry_run = True

        # Mock metadata extraction
        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.target_path is not None
        assert not result.target_path.exists()  # Target file should not be created
        assert source_file.exists()  # Original file should not be moved
        assert lyrics_file.exists()  # Lyrics stay due to dry run
        assert result.lyrics_result is not None
        assert result.lyrics_result.dry_run is True
        assert result.lyrics_result.moved is False
        assert result.lyrics_result.target_path == result.target_path.with_suffix(".lrc")
        assert (
            f"Dry run: lyrics {lyrics_file.name} would move to {result.lyrics_result.target_path.name}"
            in result.warnings
        )  # Original file should not be moved

    def test_process_directory(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test processing of a directory.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            metadata: Test metadata.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files
        music_files = ["test1.mp3", "test2.mp3"]
        image_files = ["cover.jpg"]
        other_files = ["notes.txt"]

        for name in music_files + image_files + other_files:
            (source_dir / name).touch()

        # Mock metadata extraction
        _ = mocker.patch("omym.features.metadata.usecases.file_runner.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation to return different hashes
        def mock_hash(file_path: Path) -> str:
            """Mock hash calculation that returns different hashes based on file name.

            Args:
                file_path: File path.

            Returns:
                Hash based on file name.
            """

            return f"{file_path.name}e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        _ = mocker.patch.object(processor, "_calculate_file_hash", side_effect=mock_hash)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        file_results = [r for r in results if r.source_path.suffix.lower() in processor.SUPPORTED_EXTENSIONS]
        assert len(file_results) == len(music_files)

        primary_track_name = min(music_files)
        primary_result = next(r for r in file_results if r.source_path.name == primary_track_name)
        assert len(primary_result.artwork_results) == len(image_files)
        assert all(art.moved for art in primary_result.artwork_results)
        assert primary_result.warnings == []

        non_primary_results = [r for r in file_results if r.source_path.name != primary_track_name]
        for result in non_primary_results:
            assert result.artwork_results == []

        for image in image_files:
            assert not (source_dir / image).exists()

        unprocessed_root = source_dir / UNPROCESSED_DIR_NAME
        for name in other_files:
            assert not (source_dir / name).exists()
            assert (unprocessed_root / name).exists()

        processed_files = {r.source_path.name for r in results}
        assert processed_files == set(music_files)

    def test_unprocessed_nested_files_are_relocated(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Unsupported nested files should move under the unprocessed folder."""

        source_dir = tmp_path / "tree"
        source_dir.mkdir()

        supported_file = source_dir / "Album" / "song.mp3"
        supported_file.parent.mkdir()
        unsupported_file = source_dir / "Extras" / "notes" / "info.txt"
        unsupported_file.parent.mkdir(parents=True, exist_ok=True)

        supported_file.touch()
        unsupported_file.touch()

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        _ = mocker.patch.object(
            processor,
            "_calculate_file_hash",
            side_effect=["hash-supported"],
        )

        _ = processor.process_directory(source_dir)

        unprocessed_root = source_dir / UNPROCESSED_DIR_NAME
        assert (unprocessed_root / "Extras" / "notes" / "info.txt").exists()
        assert not unsupported_file.exists()

    def test_process_directory_emits_structured_logs(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Ensure directory processing emits structured, correlated log records."""

        source_dir = tmp_path / "incoming"
        source_dir.mkdir()
        duplicate_file = source_dir / "duplicate.mp3"
        new_file = source_dir / "fresh.mp3"
        duplicate_file.touch()
        new_file.touch()

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )

        _ = mocker.patch.object(
            processor,
            "_calculate_file_hash",
            side_effect=["hash-duplicate", "hash-new", "hash-new"],
        )
        before_dao_mock = cast(MagicMock, processor.before_dao)
        before_dao_mock.check_file_exists.side_effect = [True, False, False]
        before_dao_mock.get_target_path.return_value = str(tmp_path / "library/existing.mp3")

        caplog.set_level(logging.DEBUG, logger="omym")

        results = processor.process_directory(source_dir)

        assert len(results) == 1
        assert results[0].success is True

        summary_record = next(
            record
            for record in caplog.records
            if getattr(record, "processing_event", "") == "processing.directory.complete"
        )
        summary_data = summary_record.__dict__
        assert summary_data["processed"] == 1
        assert summary_data["skipped"] == 1
        assert summary_data["failed"] == 0
        assert summary_data["directory"] == str(source_dir)

        skip_record = next(
            record
            for record in caplog.records
            if getattr(record, "processing_event", "") == "processing.file.skip.duplicate"
        )
        skip_data = skip_record.__dict__
        processed_source = str(results[0].source_path)
        expected_skip_sources = {str(duplicate_file), str(new_file)} - {processed_source}
        assert skip_data["source_path"] in expected_skip_sources
        assert str(skip_data["target_path"]).endswith("existing.mp3")

        success_record = next(
            record
            for record in caplog.records
            if getattr(record, "processing_event", "") == "processing.file.success"
        )
        success_data = success_record.__dict__
        assert success_data["artist"] == metadata.artist
        assert success_data["title"] == metadata.title
        assert float(success_data.get("duration_ms", 0.0)) >= 0.0

        process_ids = {
            getattr(record, "process_id", None)
            for record in caplog.records
            if getattr(record, "processing_event", "")
        }
        process_ids.discard(None)
        assert len(process_ids) == 1

    def test_process_directory_rollback_failure_logs_and_raises(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Rollback failures must be logged with context and raised to callers."""

        source_dir = tmp_path / "rollback"
        source_dir.mkdir()
        (source_dir / "track.mp3").touch()

        _ = mocker.patch(
            "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
            return_value=metadata,
        )
        _ = mocker.patch(
            "omym.features.metadata.usecases.directory_runner.remove_empty_directories",
            autospec=True,
        )

        conn_mock = cast(MagicMock, processor.db_manager.conn)
        conn_mock.execute.return_value = None
        conn_mock.commit.side_effect = sqlite3.Error("commit failure")
        conn_mock.rollback.side_effect = sqlite3.Error("rollback failure")

        def fake_process(file_path: Path, **_: object) -> ProcessResult:
            return ProcessResult(source_path=file_path, success=True)

        _ = mocker.patch.object(processor, "process_file", side_effect=fake_process)

        caplog.set_level(logging.ERROR, logger="omym")

        with pytest.raises(DirectoryRollbackError) as exc_info:
            _ = processor.process_directory(source_dir)

        conn_mock.rollback.assert_called_once()
        message = str(exc_info.value)
        assert "process_id=" in message
        assert str(source_dir) in message
        assert "rollback failure" in message

        rollback_records = [
            record
            for record in caplog.records
            if getattr(record, "processing_event", "")
            == ProcessingEvent.DIRECTORY_ROLLBACK_ERROR.value
        ]
        assert rollback_records
        rollback_record = rollback_records[0]
        process_id_value = getattr(rollback_record, "process_id", "")
        directory_value = getattr(rollback_record, "directory", "")
        rollback_error_value = getattr(rollback_record, "rollback_error", "")
        assert process_id_value
        assert directory_value == str(source_dir)
        assert rollback_error_value == "rollback failure"

    def test_process_file_duplicate_logs_skip(
        self,
        processor: MusicProcessor,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Duplicate files short-circuit with explicit logging context."""

        source_file = tmp_path / "song.mp3"
        source_file.touch()
        target_path = tmp_path / "library" / "song.mp3"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()

        before_dao_mock = cast(MagicMock, processor.before_dao)
        before_dao_mock.check_file_exists.return_value = True
        before_dao_mock.get_target_path.return_value = str(target_path)

        caplog.set_level(logging.DEBUG, logger="omym")

        result = processor.process_file(source_file)

        assert result.success is True
        assert result.skipped_duplicate is True
        assert result.target_path == target_path
        assert result.artwork_results == []
        assert result.warnings == []

        events = [getattr(record, "processing_event", "") for record in caplog.records]
        assert "processing.file.start" in events
        assert "processing.file.skip.duplicate" in events

        skip_record = next(
            record
            for record in caplog.records
            if getattr(record, "processing_event", "") == "processing.file.skip.duplicate"
        )
        skip_data = skip_record.__dict__
        assert skip_data["target_path"] == str(target_path)
        assert skip_data["source_path"] == str(source_file)

    def test_process_file_duplicate_same_location_marks_processed(
        self,
        processor: MusicProcessor,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Duplicates already at target should be treated as organized."""

        source_file = tmp_path / "Artist" / "Album" / "song.mp3"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()

        before_dao_mock = cast(MagicMock, processor.before_dao)
        before_dao_mock.check_file_exists.return_value = True
        before_dao_mock.get_target_path.return_value = str(source_file)

        caplog.set_level(logging.INFO, logger="omym")

        result = processor.process_file(source_file)

        assert result.success is True
        assert result.skipped_duplicate is False
        assert result.target_path == source_file
        assert source_file.exists()

        events = {getattr(record, "processing_event", "") for record in caplog.records}
        assert "processing.file.already_organized" in events

    def test_process_directory_preserves_already_organized_files(
        self,
        processor: MusicProcessor,
        tmp_path: Path,
    ) -> None:
        """Directory processing should not relocate files already at target."""

        source_dir = tmp_path / "organized"
        organized_file = source_dir / "Artist" / "Album" / "song.mp3"
        organized_file.parent.mkdir(parents=True, exist_ok=True)
        organized_file.touch()

        before_dao_mock = cast(MagicMock, processor.before_dao)
        before_dao_mock.check_file_exists.return_value = True
        before_dao_mock.get_target_path.return_value = str(organized_file)

        results = processor.process_directory(source_dir)

        assert len(results) == 1
        processed = results[0]
        assert processed.source_path == organized_file
        assert processed.skipped_duplicate is False
        assert processed.success is True

        unprocessed_root = source_dir / UNPROCESSED_DIR_NAME
        assert not unprocessed_root.exists()
        assert organized_file.exists()

    def test_cached_romanization_bypasses_musicbrainz(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
    ) -> None:
        """Ensure cached MusicBrainz romanizations skip HTTP scheduling."""

        cached_name = "米津玄師"
        cached_romanized = "Kenshi Yonezu"

        artist_dao_mock = cast(MagicMock, processor.artist_dao)
        artist_dao_mock.get_romanized_name.return_value = cached_romanized

        submit_mock = mocker.patch.object(
            processor._romanizer_executor,  # pyright: ignore[reportPrivateUsage] - tests may hook executor internals
            "submit",
            side_effect=AssertionError("Romanization task should not be scheduled on cache hit"),
        )
        processor._schedule_romanization(cached_name)  # pyright: ignore[reportPrivateUsage] - exercising cache-aware path

        assert cached_name in processor._romanize_futures  # pyright: ignore[reportPrivateUsage] - validate future caching
        future = processor._romanize_futures[cached_name]  # pyright: ignore[reportPrivateUsage] - retrieve prepared future
        assert future.result() == cached_romanized

        artist_dao_mock.upsert_romanized_name.reset_mock()

        assert processor._await_romanization(cached_name) == cached_romanized  # pyright: ignore[reportPrivateUsage] - ensure reuse
        submit_mock.assert_not_called()
        artist_dao_mock.get_romanized_name.assert_called_once_with(cached_name)
        artist_dao_mock.upsert_romanized_name.assert_called_once_with(cached_name, cached_romanized)

    def test_file_extension_safety(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test handling of unsupported file extensions.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            metadata: Test metadata.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files with various extensions
        test_files = {
            "test.mp3": True,  # Should be processed
            "test.flac": True,  # Should be processed
            "test.m4a": True,  # Should be processed
            "test.wav": False,  # Should be skipped
            "test.txt": False,  # Should be skipped
            "test": False,  # Should be skipped
        }

        for name, _ in test_files.items():
            (source_dir / name).touch()

        # Mock metadata extraction
        _ = mocker.patch("omym.features.metadata.usecases.file_runner.MetadataExtractor.extract", return_value=metadata)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        processed_files = {r.source_path.name for r in results}
        expected_files = {name for name, should_process in test_files.items() if should_process}
        assert processed_files == expected_files

        # Verify that skipped files relocate under the unprocessed folder
        unprocessed_root = source_dir / UNPROCESSED_DIR_NAME
        for name, should_process in test_files.items():
            if not should_process:
                assert not (source_dir / name).exists()
                assert (unprocessed_root / name).exists()

    def test_duplicate_file_handling(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test handling of duplicate files.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            metadata: Test metadata.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()

        # Create target directory with existing files
        target_dir = tmp_path / "Pink-Floyd" / "1979_The-Wall"
        target_dir.mkdir(parents=True)
        existing_file = target_dir / "D2_06_Comfortably-Numb_PNKFL.mp3"
        existing_file.touch()

        # Mock metadata extraction
        _ = mocker.patch("omym.features.metadata.usecases.file_runner.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation
        _ = mocker.patch.object(processor, "_calculate_file_hash", return_value=file_hash)

        # Mock database check to indicate file exists
        mock_before_dao = mocker.patch("omym.features.metadata.usecases.music_file_processor.ProcessingBeforeDAO").return_value
        mock_before_dao.check_file_exists.return_value = True
        mock_before_dao.get_target_path.return_value = str(existing_file)

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True  # File should be processed with a sequence number
        assert result.target_path is not None
        assert result.target_path.name == "D2_06_Comfortably-Numb_PNKFL (1).mp3"
        assert result.target_path.exists()
        assert not source_file.exists()  # Original file should be moved

    def test_sequence_number_handling(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test handling of sequence numbers in filenames.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            metadata: Test metadata.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()

        # Create target directory with existing files
        target_dir = tmp_path / "Pink-Floyd" / "1979_The-Wall"
        target_dir.mkdir(parents=True)
        existing_file = target_dir / "D2_06_Comfortably-Numb_PNKFL.mp3"
        existing_file.touch()

        # Mock metadata extraction
        _ = mocker.patch("omym.features.metadata.usecases.file_runner.MetadataExtractor.extract", return_value=metadata)

        # Mock database check to indicate file exists
        mock_before_dao = mocker.patch("omym.features.metadata.usecases.music_file_processor.ProcessingBeforeDAO").return_value
        mock_before_dao.check_file_exists.return_value = True
        mock_before_dao.get_target_path.return_value = str(existing_file)

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.target_path is not None
        assert result.target_path.name == "D2_06_Comfortably-Numb_PNKFL (1).mp3"
        assert result.target_path.exists()
        assert not source_file.exists()  # Original file should be moved

    def test_safe_file_operations(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test safe file operations during processing.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            metadata: Test metadata.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()

        # Mock metadata extraction
        _ = mocker.patch("omym.features.metadata.usecases.file_runner.MetadataExtractor.extract", return_value=metadata)

        # Mock shutil.move to raise an error
        mock_move = mocker.patch("omym.features.metadata.usecases.file_operations.shutil.move")
        mock_move.side_effect = OSError("Failed to move file: Test error")

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is False
        assert "Failed to move file" in str(result.error_message)
        assert source_file.exists()  # Original file should still exist

    def test_init_accepts_injected_ports(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """MusicProcessor should honour injected database and DAO ports."""

        class StubDatabaseManager:
            def __init__(self) -> None:
                self.conn: sqlite3.Connection | None = None
                self.connect_called: bool = False
                self.close_called: bool = False

            def connect(self) -> None:
                self.connect_called = True
                self.conn = sqlite3.connect(":memory:")

            def close(self) -> None:
                self.close_called = True
                if self.conn is not None:
                    self.conn.close()
                    self.conn = None

        class StubProcessingBefore:
            def __init__(self) -> None:
                self.hashes: list[str] = []

            def check_file_exists(self, file_hash: str) -> bool:
                del file_hash
                return False

            def get_target_path(self, file_hash: str) -> Path | None:  # pragma: no cover - interface compliance
                del file_hash
                return None

            def insert_file(self, file_hash: str, file_path: Path) -> bool:
                del file_path
                self.hashes.append(file_hash)
                return True

        class StubProcessingAfter:
            def __init__(self) -> None:
                self.records: list[tuple[str, Path, Path]] = []

            def insert_file(self, file_hash: str, file_path: Path, target_path: Path) -> bool:
                self.records.append((file_hash, file_path, target_path))
                return True

        class StubArtistCache:
            def __init__(self) -> None:
                self.ids: dict[str, str] = {}
                self.romanized: dict[str, str] = {}

            def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
                self.ids[artist_name] = artist_id
                return True

            def get_artist_id(self, artist_name: str) -> str | None:
                return self.ids.get(artist_name)

            def get_romanized_name(self, artist_name: str) -> str | None:
                return self.romanized.get(artist_name)

            def upsert_romanized_name(
                self,
                artist_name: str,
                romanized_name: str,
                source: str | None = None,
            ) -> bool:
                del source
                self.romanized[artist_name] = romanized_name
                return True

            def clear_cache(self) -> bool:  # pragma: no cover - interface compliance
                self.ids.clear()
                self.romanized.clear()
                return True

        stub_db = StubDatabaseManager()
        stub_before = StubProcessingBefore()
        stub_after = StubProcessingAfter()
        stub_artist = StubArtistCache()

        configure_mock = mocker.patch(
            "omym.features.metadata.usecases.music_file_processor.configure_romanization_cache"
        )

        processor = MusicProcessor(
            base_path=tmp_path,
            db_manager=stub_db,
            before_gateway=stub_before,
            after_gateway=stub_after,
            artist_cache=stub_artist,
        )

        assert processor.db_manager is stub_db
        assert processor.before_dao is stub_before
        assert processor.after_dao is stub_after
        assert processor.artist_dao is stub_artist
        assert stub_db.connect_called is True
        configure_mock.assert_called_once_with(stub_artist)

        processor.db_manager.close()


def test_dry_run_skips_persistent_state(
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Dry-run execution must leave the persistent database untouched."""

    data_dir = tmp_path / "data"
    monkeypatch.setenv("OMYM_DATA_DIR", str(data_dir))

    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "destination"
    source_dir.mkdir()
    destination_dir.mkdir()

    audio_file = source_dir / "track.mp3"
    _ = audio_file.write_bytes(b"test-audio")

    metadata = TrackMetadata(
        title="Track",
        artist=None,
        album=None,
        album_artist=None,
        file_extension=".mp3",
    )
    _ = mocker.patch(
        "omym.features.metadata.usecases.file_runner.MetadataExtractor.extract",
        return_value=metadata,
    )

    processor = MusicProcessor(base_path=destination_dir, dry_run=True)
    target_candidate = destination_dir / "Track.mp3"
    _ = mocker.patch.object(processor, "_generate_target_path", return_value=target_candidate)

    result = processor.process_file(audio_file, source_root=source_dir, target_root=destination_dir)

    assert result.success is True
    assert result.dry_run is True
    assert audio_file.exists()
    assert processor.db_manager.conn is not None

    cursor = processor.db_manager.conn.cursor()
    _ = cursor.execute("SELECT COUNT(*) FROM processing_before")
    assert cursor.fetchone()[0] == 0
    _ = cursor.execute("SELECT COUNT(*) FROM processing_after")
    assert cursor.fetchone()[0] == 0
    _ = cursor.execute("SELECT COUNT(*) FROM artist_cache")
    assert cursor.fetchone()[0] == 0

    processor._romanizer_executor.shutdown(wait=False)  # pyright: ignore[reportPrivateUsage] - executor cleanup for test
    processor.db_manager.conn.close()
