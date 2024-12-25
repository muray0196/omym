"""Tests for music file processing functionality."""

from pathlib import Path
from typing import TYPE_CHECKING, List, cast

import pytest
from pytest_mock import MockerFixture

from omym.core.metadata import TrackMetadata
from omym.core.processor import MusicProcessor, ProcessResult

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest
    from _pytest.monkeypatch import MonkeyPatch
    from _pytest.logging import LogCaptureFixture
    from _pytest.capture import CaptureFixture


@pytest.fixture
def metadata() -> TrackMetadata:
    """Create a test metadata object."""
    return TrackMetadata(
        title="Comfortably Numb",
        artist="Pink Floyd",
        album="The Wall",
        album_artist="Pink Floyd",
        year=1979,
        track_number=6,
        disc_number=2,
        file_extension=".mp3",
    )


@pytest.fixture
def file_hash() -> str:
    """Create a test file hash."""
    return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
def processor(mocker: MockerFixture, tmp_path: Path) -> MusicProcessor:
    """Create a test processor with mocked dependencies."""
    # Mock all DAOs
    mocker.patch("omym.core.processor.DatabaseManager")
    mocker.patch(
        "omym.core.processor.ArtistCacheDAO"
    ).return_value.get_artist_id.return_value = "PNKFL"
    mocker.patch(
        "omym.core.processor.ProcessingBeforeDAO"
    ).return_value.get_all_files.return_value = []
    mocker.patch(
        "omym.core.processor.ProcessingAfterDAO"
    ).return_value.get_target_path.return_value = None

    # Create processor
    processor = MusicProcessor(base_path=tmp_path)

    # Mock file hash calculation
    mocker.patch.object(processor, "_calculate_file_hash", return_value=file_hash)

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

        expected_dir = tmp_path / "Pink-Floyd/1979_The-Wall"
        expected_file = expected_dir / "D2_06_Comfortably-Numb_PNKFL.mp3"

        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract", return_value=metadata
        )

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert isinstance(result, ProcessResult)
        assert result.success is True
        assert result.source_path == source_file
        assert result.target_path == expected_file
        assert result.error_message is None
        assert result.file_hash is not None
        assert expected_file.exists()
        assert not source_file.exists()

    def test_process_file_metadata_error(
        self, mocker: MockerFixture, processor: MusicProcessor, tmp_path: Path
    ) -> None:
        """Test handling of metadata extraction error."""
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()

        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract",
            side_effect=Exception("Metadata extraction failed"),
        )

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "Metadata extraction failed" in result.error_message
        assert source_file.exists()

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

        processor.dry_run = True
        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract", return_value=metadata
        )

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.dry_run is True
        assert source_file.exists()
        assert result.target_path is not None
        assert not result.target_path.exists()

    def test_process_directory(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test processing of a directory."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files
        music_files = ["test1.mp3", "test2.mp3"]
        other_files = ["test.txt", "test.jpg"]

        for name in music_files + other_files:
            (source_dir / name).touch()

        # Mock metadata extraction
        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract", return_value=metadata
        )

        # Mock DAOs
        mock_before_dao = mocker.patch(
            "omym.core.processor.ProcessingBeforeDAO"
        ).return_value
        mock_after_dao = mocker.patch(
            "omym.core.processor.ProcessingAfterDAO"
        ).return_value
        mock_artist_dao = mocker.patch(
            "omym.core.processor.ArtistCacheDAO"
        ).return_value

        mock_before_dao.insert_file.return_value = True
        mock_before_dao.get_all_files.return_value = []
        mock_after_dao.insert_file.return_value = True
        mock_after_dao.get_target_path.return_value = None
        mock_artist_dao.get_artist_id.return_value = "PNKFL"
        mock_artist_dao.insert_artist_id.return_value = True

        # Create new processor with mocked DAOs
        processor = MusicProcessor(base_path=tmp_path)
        mocker.patch.object(processor, "_calculate_file_hash", return_value=file_hash)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        # Filter results based on file extension instead of file existence
        file_results = [
            r
            for r in results
            if r.source_path is not None
            and r.source_path.suffix.lower() in processor.SUPPORTED_EXTENSIONS
        ]
        assert len(file_results) == len(music_files)

        for result in file_results:
            assert result.success is True
            assert result.target_path is not None
            assert result.target_path.exists()
            assert result.source_path is not None
            assert not result.source_path.exists()  # Original file should be moved

        # Non-music files should still exist
        for name in other_files:
            assert (source_dir / name).exists()

        # Verify that only supported files were processed
        processed_files = {cast(Path, r.source_path).name for r in file_results}
        assert processed_files == set(music_files)

    def test_file_extension_safety(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test that file extensions are preserved and not modified during processing."""
        # Arrange
        extensions = [".mp3", ".flac", ".m4a"]
        test_files: List[Path] = []
        expected_files: List[Path] = []

        for i, ext in enumerate(extensions, 1):
            # Create test file with specific extension
            source_file = tmp_path / f"test{i}{ext}"
            source_file.touch()
            test_files.append(source_file)

            # Create expected file path
            test_metadata = TrackMetadata(
                title=metadata.title,
                artist=metadata.artist,
                album=metadata.album,
                album_artist=metadata.album_artist,
                year=metadata.year,
                track_number=metadata.track_number,
                disc_number=metadata.disc_number,
                file_extension=ext,
            )
            expected_dir = tmp_path / "Pink-Floyd/1979_The-Wall"
            expected_file = expected_dir / f"D2_06_Comfortably-Numb_PNKFL{ext}"
            expected_files.append(expected_file)

            # Mock metadata extraction for this file
            mocker.patch(
                "omym.core.processor.MetadataExtractor.extract",
                return_value=test_metadata,
            )

            # Process the file
            result = processor.process_file(source_file)

            # Verify extension preservation
            assert result.success is True
            assert result.target_path is not None
            assert result.target_path == expected_file
            assert result.target_path.suffix == ext
            assert expected_file.exists()
            assert expected_file.suffix == ext

    def test_duplicate_file_safety(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test that duplicate file handling is safe and preserves all files."""
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()
        source_content = b"test content"
        source_file.write_bytes(source_content)

        # Create a file that should not be affected
        unrelated_file = tmp_path / "unrelated.mp3"
        unrelated_file.touch()
        unrelated_content = b"different content"
        unrelated_file.write_bytes(unrelated_content)

        # Create existing file (duplicate)
        existing_dir = tmp_path / "Pink-Floyd/1979_The-Wall"
        existing_dir.mkdir(parents=True, exist_ok=True)
        existing_file = existing_dir / "D2_06_Comfortably-Numb_PNKFL.mp3"
        existing_file.touch()
        existing_file.write_bytes(source_content)  # Same content as source_file

        # Expected path for the duplicate file
        expected_file = existing_dir / "D2_06_Comfortably-Numb_PNKFL_1.mp3"

        # Mock hash calculation to return different hashes based on content
        def mock_hash(file_path: Path) -> str:
            content = file_path.read_bytes()
            if content == source_content:
                return "hash1"
            return "hash2"

        mocker.patch.object(processor, "_calculate_file_hash", side_effect=mock_hash)

        # Mock metadata extraction
        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract", return_value=metadata
        )

        # Mock DAOs to indicate existing file is a duplicate
        mock_before_dao = mocker.patch(
            "omym.core.processor.ProcessingBeforeDAO"
        ).return_value
        mock_after_dao = mocker.patch(
            "omym.core.processor.ProcessingAfterDAO"
        ).return_value

        mock_before_dao.get_all_files.return_value = [
            (existing_file, "hash1", metadata)  # Same hash as source_file
        ]
        mock_after_dao.get_target_path.return_value = existing_file

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.target_path == expected_file
        assert not source_file.exists()  # Source file should be moved
        assert existing_file.exists()  # Original file should remain
        assert (
            expected_file.exists()
        )  # Duplicate file should be moved with sequence number
        assert unrelated_file.exists()  # Unrelated file should not be touched
        assert (
            unrelated_file.read_bytes() == unrelated_content
        )  # Content should be preserved

    def test_sequence_number_handling(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test that sequence numbers are correctly added to file names."""
        # Arrange
        source_files = [tmp_path / f"test{i}.mp3" for i in range(3)]
        for file in source_files:
            file.touch()

        # Create target directory
        target_dir = tmp_path / "Pink-Floyd/1979_The-Wall"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Expected files with sequence numbers
        expected_files = [
            target_dir / "D2_06_Comfortably-Numb_PNKFL.mp3",
            target_dir / "D2_06_Comfortably-Numb_PNKFL_1.mp3",
            target_dir / "D2_06_Comfortably-Numb_PNKFL_2.mp3",
        ]

        # Mock metadata extraction
        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract", return_value=metadata
        )

        # Process each file
        results = []
        for file in source_files:
            result = processor.process_file(file)
            results.append(result)

        # Assert
        for i, (result, expected_file) in enumerate(zip(results, expected_files)):
            assert result.success is True
            assert result.target_path == expected_file
            assert not source_files[i].exists()  # Source file should be moved
            assert expected_file.exists()  # Target file should exist

        # Verify all files have been preserved
        assert len(list(target_dir.glob("*.mp3"))) == len(source_files)

    def test_safe_file_operations(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test that file operations (move/delete) only affect intended files."""
        # Arrange
        # Create directory structure
        music_dir = tmp_path / "music"
        other_dir = tmp_path / "other"
        music_dir.mkdir()
        other_dir.mkdir()

        # Create test files
        music_file = music_dir / "test.mp3"
        music_file.touch()
        other_files = [
            other_dir / "document.txt",
            other_dir / "image.jpg",
            other_dir / "test.mp3",  # Same name but different directory
        ]
        for file in other_files:
            file.touch()

        # Record initial state
        initial_files = set(f for f in tmp_path.rglob("*") if f.is_file())

        # Mock metadata extraction
        mocker.patch(
            "omym.core.processor.MetadataExtractor.extract", return_value=metadata
        )

        # Act
        result = processor.process_file(music_file)

        # Assert
        assert result.success is True
        assert result.target_path is not None
        assert result.target_path.exists()
        assert not music_file.exists()  # Only the processed file should be moved

        # Verify other files are untouched
        for file in other_files:
            assert file.exists(), f"Unrelated file {file} was affected"

        # Verify no unexpected files were created or deleted
        current_files = set(f for f in tmp_path.rglob("*") if f.is_file())
        expected_files = (initial_files - {music_file}) | {result.target_path}
        assert current_files == expected_files, "Unexpected changes to file system"

        # Verify directory structure is preserved
        assert other_dir.exists()
        assert len(list(other_dir.iterdir())) == len(other_files)
