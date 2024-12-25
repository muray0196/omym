"""Tests for metadata extraction functionality."""

from pathlib import Path
from typing import Dict, List, Tuple, Union

import pytest
from pytest_mock import MockerFixture

from omym.core.metadata_extractor import MetadataExtractor, TrackMetadata


@pytest.fixture
def mock_mp3_metadata() -> Dict[str, List[str]]:
    """Mock MP3 metadata.

    Returns:
        Dictionary containing mock MP3 metadata.
    """
    return {
        "title": ["Test Title"],
        "artist": ["Test Artist"],
        "albumartist": ["Test Album Artist"],
        "album": ["Test Album"],
        "tracknumber": ["1/12"],
        "discnumber": ["1/2"],
        "date": ["2023"],
    }


@pytest.fixture
def mock_flac_metadata() -> Dict[str, List[str]]:
    """Mock FLAC metadata.

    Returns:
        Dictionary containing mock FLAC metadata.
    """
    return {
        "title": ["Test Title"],
        "artist": ["Test Artist"],
        "albumartist": ["Test Album Artist"],
        "album": ["Test Album"],
        "tracknumber": ["1/12"],
        "discnumber": ["1/2"],
        "date": ["2023"],
    }


@pytest.fixture
def mock_m4a_metadata() -> Dict[str, Union[List[str], List[Tuple[int, int]]]]:
    """Mock M4A metadata.

    Returns:
        Dictionary containing mock M4A metadata.
    """
    return {
        "\xa9nam": ["Test Title"],
        "\xa9ART": ["Test Artist"],
        "aART": ["Test Album Artist"],
        "\xa9alb": ["Test Album"],
        "trkn": [(1, 12)],
        "disk": [(1, 2)],
        "\xa9day": ["2023"],
    }


class TestMetadataExtractor:
    """Test cases for MetadataExtractor."""

    def test_unsupported_format(self) -> None:
        """Test extraction with unsupported file format."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            MetadataExtractor.extract(Path("test.wav"))

    def test_nonexistent_file(self) -> None:
        """Test extraction with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            MetadataExtractor.extract(Path("nonexistent.mp3"))

    def test_mp3_extraction(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        mock_mp3_metadata: Dict[str, List[str]],
    ) -> None:
        """Test MP3 metadata extraction."""
        # Create test file
        test_file = tmp_path / "test.mp3"
        test_file.touch()

        # Setup mock
        mocker.patch.object(
            MetadataExtractor,
            "_extract_mp3",
            return_value=TrackMetadata(
                title="Test Title",
                artist="Test Artist",
                album_artist="Test Album Artist",
                album="Test Album",
                track_number=1,
                track_total=12,
                disc_number=1,
                disc_total=2,
                year=2023,
                file_extension=".mp3",
            ),
        )

        try:
            # Test extraction
            metadata = MetadataExtractor.extract(test_file)

            assert isinstance(metadata, TrackMetadata)
            assert metadata.file_extension == ".mp3"
            assert metadata.title == "Test Title"
            assert metadata.artist == "Test Artist"
            assert metadata.album_artist == "Test Album Artist"
            assert metadata.album == "Test Album"
            assert metadata.track_number == 1
            assert metadata.track_total == 12
            assert metadata.disc_number == 1
            assert metadata.disc_total == 2
            assert metadata.year == 2023
        finally:
            # Clean up
            test_file.unlink()

    def test_flac_extraction(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        mock_flac_metadata: Dict[str, List[str]],
    ) -> None:
        """Test FLAC metadata extraction."""
        # Create test file
        test_file = tmp_path / "test.flac"
        test_file.touch()

        # Setup mock
        mocker.patch.object(
            MetadataExtractor,
            "_extract_flac",
            return_value=TrackMetadata(
                title="Test Title",
                artist="Test Artist",
                album_artist="Test Album Artist",
                album="Test Album",
                track_number=1,
                track_total=12,
                disc_number=1,
                disc_total=2,
                year=2023,
                file_extension=".flac",
            ),
        )

        try:
            # Test extraction
            metadata = MetadataExtractor.extract(test_file)

            assert isinstance(metadata, TrackMetadata)
            assert metadata.file_extension == ".flac"
            assert metadata.title == "Test Title"
            assert metadata.artist == "Test Artist"
            assert metadata.album_artist == "Test Album Artist"
            assert metadata.album == "Test Album"
            assert metadata.track_number == 1
            assert metadata.track_total == 12
            assert metadata.disc_number == 1
            assert metadata.disc_total == 2
            assert metadata.year == 2023
        finally:
            # Clean up
            test_file.unlink()

    def test_m4a_extraction(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        mock_m4a_metadata: Dict[str, Union[List[str], List[Tuple[int, int]]]],
    ) -> None:
        """Test M4A metadata extraction."""
        # Create test file
        test_file = tmp_path / "test.m4a"
        test_file.touch()

        # Setup mock
        mocker.patch.object(
            MetadataExtractor,
            "_extract_m4a",
            return_value=TrackMetadata(
                title="Test Title",
                artist="Test Artist",
                album_artist="Test Album Artist",
                album="Test Album",
                track_number=1,
                track_total=12,
                disc_number=1,
                disc_total=2,
                year=2023,
                file_extension=".m4a",
            ),
        )

        try:
            # Test extraction
            metadata = MetadataExtractor.extract(test_file)

            assert isinstance(metadata, TrackMetadata)
            assert metadata.file_extension == ".m4a"
            assert metadata.title == "Test Title"
            assert metadata.artist == "Test Artist"
            assert metadata.album_artist == "Test Album Artist"
            assert metadata.album == "Test Album"
            assert metadata.track_number == 1
            assert metadata.track_total == 12
            assert metadata.disc_number == 1
            assert metadata.disc_total == 2
            assert metadata.year == 2023
        finally:
            # Clean up
            test_file.unlink()

    def test_missing_metadata(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test extraction with missing metadata fields."""
        # Create test file
        test_file = tmp_path / "test.mp3"
        test_file.touch()

        # Setup mock
        mocker.patch.object(
            MetadataExtractor,
            "_extract_mp3",
            return_value=TrackMetadata(
                title="Test Title",
                artist=None,
                album_artist=None,
                album=None,
                track_number=None,
                track_total=None,
                disc_number=None,
                disc_total=None,
                year=None,
                file_extension=".mp3",
            ),
        )

        try:
            metadata = MetadataExtractor.extract(test_file)
            assert isinstance(metadata, TrackMetadata)
            assert metadata.title == "Test Title"
            assert metadata.artist is None
            assert metadata.album_artist is None
            assert metadata.album is None
            assert metadata.track_number is None
            assert metadata.track_total is None
            assert metadata.disc_number is None
            assert metadata.disc_total is None
            assert metadata.year is None
        finally:
            # Clean up
            test_file.unlink()
