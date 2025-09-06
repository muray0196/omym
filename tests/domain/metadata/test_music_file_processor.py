"""Tests for music file processing functionality."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.metadata.music_file_processor import MusicProcessor


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
def processor(mocker: MockerFixture, tmp_path: Path) -> MusicProcessor:
    """Create a test processor with mocked dependencies.

    Args:
        mocker: Pytest mocker fixture.
        tmp_path: Temporary path fixture.

    Returns:
        MusicProcessor: A test processor.
    """
    # Mock database manager
    mock_db = mocker.patch("omym.domain.metadata.music_file_processor.DatabaseManager").return_value
    mock_db.conn = mocker.MagicMock()

    # Mock DAOs
    mock_before_dao = mocker.patch("omym.domain.metadata.music_file_processor.ProcessingBeforeDAO").return_value
    mock_after_dao = mocker.patch("omym.domain.metadata.music_file_processor.ProcessingAfterDAO").return_value
    mock_artist_dao = mocker.patch("omym.domain.metadata.music_file_processor.ArtistCacheDAO").return_value

    # Configure DAO behavior
    _ = mock_before_dao.check_file_exists.return_value = False
    _ = mock_before_dao.insert_file.return_value = True
    _ = mock_after_dao.insert_file.return_value = True
    _ = mock_artist_dao.get_artist_id.return_value = "PNKFL"
    _ = mock_artist_dao.insert_artist_id.return_value = True

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
        """Test successful processing of a single music file.

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
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.target_path is not None
        assert result.target_path.exists()
        assert not source_file.exists()  # Original file should be moved

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
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=None)

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
        """Test dry run mode.

        Args:
            mocker: Pytest mocker fixture.
            processor: Test processor.
            metadata: Test metadata.
            tmp_path: Temporary path fixture.
        """
        # Arrange
        source_file = tmp_path / "test.mp3"
        source_file.touch()
        processor.dry_run = True

        # Mock metadata extraction
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is True
        assert result.target_path is not None
        assert not result.target_path.exists()  # Target file should not be created
        assert source_file.exists()  # Original file should not be moved

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
        other_files = ["test.txt", "test.jpg"]

        for name in music_files + other_files:
            (source_dir / name).touch()

        # Mock metadata extraction
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

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
        # Filter results based on file extension
        file_results = [r for r in results if r.source_path.suffix.lower() in processor.SUPPORTED_EXTENSIONS]
        assert len(file_results) == len(music_files)

        for result in file_results:
            assert result.success is True

        # Non-music files should still exist
        for name in other_files:
            assert (source_dir / name).exists()

        # Verify that only supported files were processed
        processed_files = {r.source_path.name for r in results}
        assert processed_files == set(music_files)

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
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        processed_files = {r.source_path.name for r in results}
        expected_files = {name for name, should_process in test_files.items() if should_process}
        assert processed_files == expected_files

        # Verify that skipped files still exist
        for name, should_process in test_files.items():
            if not should_process:
                assert (source_dir / name).exists()

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
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation
        _ = mocker.patch.object(processor, "_calculate_file_hash", return_value=file_hash)

        # Mock database check to indicate file exists
        mock_before_dao = mocker.patch("omym.domain.metadata.music_file_processor.ProcessingBeforeDAO").return_value
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
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

        # Mock database check to indicate file exists
        mock_before_dao = mocker.patch("omym.domain.metadata.music_file_processor.ProcessingBeforeDAO").return_value
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
        _ = mocker.patch("omym.domain.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)

        # Mock shutil.move to raise an error
        mock_move = mocker.patch("omym.domain.metadata.music_file_processor.shutil.move")
        mock_move.side_effect = OSError("Failed to move file: Test error")

        # Act
        result = processor.process_file(source_file)

        # Assert
        assert result.success is False
        assert "Failed to move file" in str(result.error_message)
        assert source_file.exists()  # Original file should still exist
