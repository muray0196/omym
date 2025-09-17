"""Tests for metadata extraction functionality."""

from pathlib import Path
from typing import TypeAlias

import pytest
from pytest_mock import MockerFixture

from omym.domain.metadata.artist_romanizer import ArtistRomanizer
from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.metadata.track_metadata_extractor import MetadataExtractor

# Type aliases for metadata dictionaries
MP3Metadata: TypeAlias = dict[str, list[str]]
FLACMetadata: TypeAlias = dict[str, list[str]]
M4AMetadata: TypeAlias = dict[str, list[str] | list[tuple[int, int]]]


@pytest.fixture
def mock_mp3_metadata() -> MP3Metadata:
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
def mock_flac_metadata() -> FLACMetadata:
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
def mock_m4a_metadata() -> M4AMetadata:
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
            _ = MetadataExtractor.extract(Path("test.wav"))

    def test_nonexistent_file(self) -> None:
        """Test extraction with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            _ = MetadataExtractor.extract(Path("nonexistent.mp3"))

    def test_mp3_extraction(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        mock_mp3_metadata: MP3Metadata,
    ) -> None:
        """Test MP3 metadata extraction.

        Args:
            tmp_path: Pytest temporary path fixture.
            mocker: Pytest mocker fixture.
            mock_mp3_metadata: Mock MP3 metadata fixture.
        """
        # Create test file
        test_file = tmp_path / "test.mp3"
        test_file.touch()

        # Get metadata values with proper type assertions
        title = mock_mp3_metadata["title"][0]
        assert isinstance(title, str)
        artist = mock_mp3_metadata["artist"][0]
        assert isinstance(artist, str)
        album_artist = mock_mp3_metadata["albumartist"][0]
        assert isinstance(album_artist, str)
        album = mock_mp3_metadata["album"][0]
        assert isinstance(album, str)
        track_info = mock_mp3_metadata["tracknumber"][0].split("/")
        track_number = int(track_info[0])
        track_total = int(track_info[1])
        disc_info = mock_mp3_metadata["discnumber"][0].split("/")
        disc_number = int(disc_info[0])
        disc_total = int(disc_info[1])
        year_str = mock_mp3_metadata["date"][0]
        assert isinstance(year_str, str)
        year = int(year_str)

        # Setup mock
        _ = mocker.patch.object(
            MetadataExtractor,
            "_extract_mp3",
            return_value=TrackMetadata(
                title=title,
                artist=artist,
                album_artist=album_artist,
                album=album,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=".mp3",
            ),
        )

        try:
            # Test extraction
            metadata = MetadataExtractor.extract(test_file)

            assert isinstance(metadata, TrackMetadata)
            assert metadata.file_extension == ".mp3"
            assert metadata.title == title
            assert metadata.artist == artist
            assert metadata.album_artist == album_artist
            assert metadata.album == album
            assert metadata.track_number == track_number
            assert metadata.track_total == track_total
            assert metadata.disc_number == disc_number
            assert metadata.disc_total == disc_total
            assert metadata.year == year
        finally:
            # Clean up
            test_file.unlink()

    def test_flac_extraction(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        mock_flac_metadata: FLACMetadata,
    ) -> None:
        """Test FLAC metadata extraction.

        Args:
            tmp_path: Pytest temporary path fixture.
            mocker: Pytest mocker fixture.
            mock_flac_metadata: Mock FLAC metadata fixture.
        """
        # Create test file
        test_file = tmp_path / "test.flac"
        test_file.touch()

        # Get metadata values with proper type assertions
        title = mock_flac_metadata["title"][0]
        assert isinstance(title, str)
        artist = mock_flac_metadata["artist"][0]
        assert isinstance(artist, str)
        album_artist = mock_flac_metadata["albumartist"][0]
        assert isinstance(album_artist, str)
        album = mock_flac_metadata["album"][0]
        assert isinstance(album, str)
        track_info = mock_flac_metadata["tracknumber"][0].split("/")
        track_number = int(track_info[0])
        track_total = int(track_info[1])
        disc_info = mock_flac_metadata["discnumber"][0].split("/")
        disc_number = int(disc_info[0])
        disc_total = int(disc_info[1])
        year_str = mock_flac_metadata["date"][0]
        assert isinstance(year_str, str)
        year = int(year_str)

        # Setup mock
        _ = mocker.patch.object(
            MetadataExtractor,
            "_extract_flac",
            return_value=TrackMetadata(
                title=title,
                artist=artist,
                album_artist=album_artist,
                album=album,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=".flac",
            ),
        )

        try:
            # Test extraction
            metadata = MetadataExtractor.extract(test_file)

            assert isinstance(metadata, TrackMetadata)
            assert metadata.file_extension == ".flac"
            assert metadata.title == title
            assert metadata.artist == artist
            assert metadata.album_artist == album_artist
            assert metadata.album == album
            assert metadata.track_number == track_number
            assert metadata.track_total == track_total
            assert metadata.disc_number == disc_number
            assert metadata.disc_total == disc_total
            assert metadata.year == year
        finally:
            # Clean up
            test_file.unlink()

    def test_metadata_extractor_applies_romanization(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Verify that romanization is applied when configured to do so."""

        test_file = tmp_path / "test.mp3"
        test_file.touch()

        romanizer = ArtistRomanizer(enabled_supplier=lambda: True, fetcher=lambda _: "Hikaru Utada")
        MetadataExtractor.configure_romanizer(romanizer)

        _ = mocker.patch.object(
            MetadataExtractor,
            "_extract_mp3",
            return_value=TrackMetadata(artist="宇多田ヒカル", album_artist="宇多田ヒカル", file_extension=".mp3"),
        )

        try:
            metadata = MetadataExtractor.extract(test_file)
            assert metadata.artist == "Hikaru Utada"
            assert metadata.album_artist == "Hikaru Utada"
        finally:
            MetadataExtractor.configure_romanizer(ArtistRomanizer())
            test_file.unlink()

    def test_m4a_extraction(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        mock_m4a_metadata: M4AMetadata,
    ) -> None:
        """Test M4A metadata extraction.

        Args:
            tmp_path: Pytest temporary path fixture.
            mocker: Pytest mocker fixture.
            mock_m4a_metadata: Mock M4A metadata fixture.
        """
        # Create test file
        test_file = tmp_path / "test.m4a"
        test_file.touch()

        # Get metadata values with proper type assertions
        title = mock_m4a_metadata["\xa9nam"][0]
        assert isinstance(title, str)
        artist = mock_m4a_metadata["\xa9ART"][0]
        assert isinstance(artist, str)
        album_artist = mock_m4a_metadata["aART"][0]
        assert isinstance(album_artist, str)
        album = mock_m4a_metadata["\xa9alb"][0]
        assert isinstance(album, str)
        track_info = mock_m4a_metadata["trkn"][0]
        assert isinstance(track_info, tuple)
        track_number, track_total = track_info
        disc_info = mock_m4a_metadata["disk"][0]
        assert isinstance(disc_info, tuple)
        disc_number, disc_total = disc_info
        year_str = mock_m4a_metadata["\xa9day"][0]
        assert isinstance(year_str, str)
        year = int(year_str)

        # Setup mock
        _ = mocker.patch.object(
            MetadataExtractor,
            "_extract_m4a",
            return_value=TrackMetadata(
                title=title,
                artist=artist,
                album_artist=album_artist,
                album=album,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                year=year,
                file_extension=".m4a",
            ),
        )

        try:
            # Test extraction
            metadata = MetadataExtractor.extract(test_file)

            assert isinstance(metadata, TrackMetadata)
            assert metadata.file_extension == ".m4a"
            assert metadata.title == title
            assert metadata.artist == artist
            assert metadata.album_artist == album_artist
            assert metadata.album == album
            assert metadata.track_number == track_number
            assert metadata.track_total == track_total
            assert metadata.disc_number == disc_number
            assert metadata.disc_total == disc_total
            assert metadata.year == year
        finally:
            # Clean up
            test_file.unlink()

    def test_missing_metadata(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test extraction with missing metadata fields.

        Args:
            tmp_path: Pytest temporary path fixture.
            mocker: Pytest mocker fixture.
        """
        # Create test file
        test_file = tmp_path / "test.mp3"
        test_file.touch()

        # Setup mock
        _ = mocker.patch.object(
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
