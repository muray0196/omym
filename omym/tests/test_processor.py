"""Tests for music file processing functionality."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from omym.core.metadata import TrackMetadata
from omym.core.processor import MusicProcessor


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
        disc_number=2,
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
    mock_db = mocker.patch("omym.core.processor.DatabaseManager").return_value
    mock_db.conn = mocker.MagicMock()

    # Mock DAOs
    mock_before_dao = mocker.patch("omym.core.processor.ProcessingBeforeDAO").return_value
    mock_after_dao = mocker.patch("omym.core.processor.ProcessingAfterDAO").return_value
    mock_artist_dao = mocker.patch("omym.core.processor.ArtistCacheDAO").return_value

    # Configure DAO behavior
    mock_before_dao.check_file_exists.return_value = False
    mock_before_dao.insert_file.return_value = True
    mock_after_dao.insert_file.return_value = True
    mock_artist_dao.get_artist_id.return_value = "PNKFL"
    mock_artist_dao.insert_artist_id.return_value = True

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
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

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
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=None)

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
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

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
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation to return different hashes
        def mock_hash(file_path: Path) -> str:
            """Mock hash calculation that returns different hashes based on file name.

            Args:
                file_path: File path.

            Returns:
                Hash based on file name.
            """
            return (
                f"{file_path.name}e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )

        mocker.patch.object(processor, "_calculate_file_hash", side_effect=mock_hash)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        # Filter results based on file extension
        file_results = [
            r for r in results if r.source_path.suffix.lower() in processor.SUPPORTED_EXTENSIONS
        ]
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
            "test.dsf": True,  # Should be processed
            "test.wav": False,  # Should be skipped
            "test.ogg": False,  # Should be skipped
            "test.txt": False,  # Should be skipped
        }

        for name, _ in test_files.items():
            (source_dir / name).touch()

        # Mock metadata extraction
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation to return different hashes
        def mock_hash(file_path: Path) -> str:
            """Mock hash calculation that returns different hashes based on file name.

            Args:
                file_path: File path.

            Returns:
                Hash based on file name.
            """
            return (
                f"{file_path.name}e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )

        mocker.patch.object(processor, "_calculate_file_hash", side_effect=mock_hash)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        processed_files = {r.source_path.name for r in results if r.success}
        expected_files = {name for name, should_process in test_files.items() if should_process}
        assert processed_files == expected_files

        # Verify that unsupported files still exist
        for name, should_process in test_files.items():
            if not should_process:
                assert (source_dir / name).exists()

    def test_duplicate_file_safety(
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
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files
        test_files = ["test1.mp3", "test2.mp3", "test3.mp3"]
        for name in test_files:
            (source_dir / name).touch()

        # Mock metadata extraction
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation to return the same hash for all files
        same_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        mocker.patch.object(processor, "_calculate_file_hash", return_value=same_hash)

        # Configure mock DAO behavior for duplicate files
        mock_before_dao = mocker.MagicMock()
        mock_before_dao.check_file_exists.side_effect = [False, True, True]
        mock_before_dao.insert_file.return_value = True
        mock_before_dao.get_target_path.return_value = None
        processor.before_dao = mock_before_dao

        # Mock after DAO
        mock_after_dao = mocker.MagicMock()
        mock_after_dao.insert_file.return_value = True
        processor.after_dao = mock_after_dao

        # Mock shutil.move to simulate file movement
        def mock_move(src: str | Path, dst: str | Path) -> None:
            Path(src).unlink()
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).touch()

        mocker.patch("shutil.move", side_effect=mock_move)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        # Only the first file should be processed
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == 1

        # The first file should be moved
        assert not successful_results[0].source_path.exists()
        assert successful_results[0].target_path is not None
        assert successful_results[0].target_path.exists()

        # Other files should still exist
        remaining_files = [f for f in test_files if f != successful_results[0].source_path.name]
        for name in remaining_files:
            assert (source_dir / name).exists()

    def test_sequence_number_handling(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test handling of sequence numbers for duplicate target paths.

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
        test_files = ["test1.mp3", "test2.mp3", "test3.mp3"]
        for name in test_files:
            (source_dir / name).touch()

        # Mock metadata extraction
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation to return different hashes
        def mock_hash(file_path: Path) -> str:
            """Mock hash calculation that returns different hashes based on file name.

            Args:
                file_path: File path.

            Returns:
                Hash based on file name.
            """
            return (
                f"{file_path.name}e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )

        mocker.patch.object(processor, "_calculate_file_hash", side_effect=mock_hash)

        # Configure mock DAO behavior
        mock_before_dao = mocker.MagicMock()
        mock_before_dao.check_file_exists.return_value = False
        mock_before_dao.insert_file.return_value = True
        processor.before_dao = mock_before_dao

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == len(test_files)

        # Verify that target paths have sequence numbers
        target_paths = [r.target_path for r in successful_results if r.target_path is not None]
        assert len(target_paths) == len(test_files)
        assert len(set(target_paths)) == len(test_files)  # All paths should be unique

        # Verify that original files are moved
        for result in successful_results:
            assert not result.source_path.exists()
            assert result.target_path is not None
            assert result.target_path.exists()

    def test_safe_file_operations(
        self,
        mocker: MockerFixture,
        processor: MusicProcessor,
        metadata: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Test safe file operations.

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
        test_files = ["test1.mp3", "test2.mp3"]
        for name in test_files:
            (source_dir / name).touch()

        # Mock metadata extraction
        mocker.patch("omym.core.processor.MetadataExtractor.extract", return_value=metadata)

        # Mock file hash calculation to return different hashes
        def mock_hash(file_path: Path) -> str:
            """Mock hash calculation that returns different hashes based on file name.

            Args:
                file_path: File path.

            Returns:
                Hash based on file name.
            """
            return (
                f"{file_path.name}e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )

        mocker.patch.object(processor, "_calculate_file_hash", side_effect=mock_hash)

        # Configure mock DAO behavior
        mock_before_dao = mocker.MagicMock()
        mock_before_dao.check_file_exists.return_value = False
        mock_before_dao.insert_file.return_value = True
        processor.before_dao = mock_before_dao

        # Mock shutil.move to fail for the second file
        def mock_move(src: Path | str, dst: Path | str) -> None:
            """Mock move operation.

            Args:
                src: Source path.
                dst: Destination path.
            """
            src_path = Path(src)
            dst_path = Path(dst)

            # First call succeeds, second call fails
            if src_path.name == "test1.mp3":
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                dst_path.touch()
                src_path.unlink()
            else:
                raise OSError("Mock move error")

        mocker.patch("omym.core.processor.shutil.move", side_effect=mock_move)

        # Act
        results = processor.process_directory(source_dir)

        # Assert
        # First file should be processed successfully
        assert results[0].success is True
        assert not Path(source_dir / "test1.mp3").exists()
        assert results[0].target_path is not None
        assert results[0].target_path.exists()

        # Second file should fail with the move error
        assert results[1].success is False
        assert "Mock move error" in str(results[1].error_message)
        assert Path(source_dir / "test2.mp3").exists()  # Original file should still exist
