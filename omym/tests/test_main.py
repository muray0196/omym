"""Tests for main entry points."""

import sys
import tempfile
from pathlib import Path
import pytest
from pytest_mock import MockerFixture

from omym.core.metadata import TrackMetadata


@pytest.fixture
def test_file():
    """Create a temporary test file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir) / "test.mp3"
        test_path.touch()
        yield str(test_path)


@pytest.fixture
def mock_metadata(mocker: MockerFixture):
    """Mock metadata extraction."""
    metadata = TrackMetadata(
        title="Test Title",
        artist="Test Artist",
        album="Test Album",
        album_artist="Test Album Artist",
        genre="Test Genre",
        year=2024,
        track_number=1,
        track_total=10,
        disc_number=1,
        disc_total=1,
        file_extension=".mp3",
    )
    mocker.patch(
        "omym.core.metadata_extractor.MetadataExtractor.extract", return_value=metadata
    )


def test_main_module_entry_point(
    mocker: MockerFixture, test_file: str, mock_metadata
) -> None:
    """Test the main entry point when running as a module."""
    # Mock sys.argv to provide required arguments
    mocker.patch("sys.argv", ["omym", "process", test_file])

    # Import the module
    import omym.__main__

    # Execute the code in __main__ block
    if hasattr(omym.__main__, "__main_block__"):
        omym.__main__.__main_block__()
    else:
        omym.__main__.main()


def test_main_script_entry_point(
    mocker: MockerFixture, test_file: str, mock_metadata
) -> None:
    """Test the main entry point when running as a script."""
    # Mock sys.argv to provide required arguments
    mocker.patch("sys.argv", ["omym", "process", test_file])

    # Import the module
    import omym.main

    # Execute the code in __main__ block
    if hasattr(omym.main, "__main_block__"):
        omym.main.__main_block__()
    else:
        omym.main.main()


def test_main_module_import(
    mocker: MockerFixture, test_file: str, mock_metadata
) -> None:
    """Test importing the main module without running it."""
    # Mock sys.argv to provide required arguments
    mocker.patch("sys.argv", ["omym", "process", test_file])

    # Import the module
    import omym.__main__


def test_main_script_import(
    mocker: MockerFixture, test_file: str, mock_metadata
) -> None:
    """Test importing the main script without running it."""
    # Mock sys.argv to provide required arguments
    mocker.patch("sys.argv", ["omym", "process", test_file])

    # Import the module
    import omym.main
