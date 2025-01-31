"""Tests for main entry points."""

import tempfile
from collections.abc import Generator, Callable
from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture

from omym.core.metadata.track_metadata import TrackMetadata
from omym.core.metadata.music_file_processor import ProcessResult


@pytest.fixture
def test_file() -> Generator[str, None, None]:
    """Create a temporary test file.

    Yields:
        str: Path to the temporary test file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir) / "test.mp3"
        test_path.touch()
        yield str(test_path)


@pytest.fixture
def mock_metadata(mocker: MockerFixture) -> TrackMetadata:
    """Mock metadata extraction.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        TrackMetadata: Mock metadata for testing.
    """
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
    _ = mocker.patch("omym.core.metadata.music_file_processor.MetadataExtractor.extract", return_value=metadata)
    return metadata


@pytest.fixture
def mock_database(mocker: MockerFixture) -> None:
    """Mock database operations.

    Args:
        mocker: Pytest mocker fixture.
    """
    # Mock database manager
    mock_db = mocker.patch("omym.core.metadata.music_file_processor.DatabaseManager")
    mock_instance = mock_db.return_value
    _ = mock_instance.connect.return_value

    # Mock DAOs
    mock_before_dao = mocker.patch("omym.core.metadata.music_file_processor.ProcessingBeforeDAO")
    mock_before_instance = mock_before_dao.return_value
    _ = mock_before_instance.insert_file.return_value
    _ = mock_before_instance.check_file_exists.return_value

    mock_after_dao = mocker.patch("omym.core.metadata.music_file_processor.ProcessingAfterDAO")
    mock_after_instance = mock_after_dao.return_value
    _ = mock_after_instance.insert_file.return_value


def test_main_module_entry_point(mocker: MockerFixture, test_file: str, mock_metadata: TrackMetadata) -> None:
    """Test the main entry point when running as a module.

    Args:
        mocker: Pytest mocker fixture.
        test_file: Path to test file.
        mock_metadata: Mock metadata fixture.
    """
    # Mock sys.argv to provide required arguments
    _ = mocker.patch("sys.argv", ["omym", test_file])

    # Mock file processing
    mock_processor = mocker.patch("omym.ui.cli.commands.executor.MusicProcessor")
    mock_instance = mock_processor.return_value
    mock_instance.process_file.return_value = ProcessResult(
        source_path=Path(test_file),
        target_path=Path("Artist/Album/01 - Test Track.mp3"),
        success=True,
        metadata=mock_metadata,
        artist_id=None,
    )

    # Import and execute the module
    import omym.__main__ as main_module

    if hasattr(main_module, "__main_block__"):
        main_block: Callable[[], Any] = getattr(main_module, "__main_block__")
        main_block()
    else:
        main_module.main()  # pyright: ignore[reportPrivateLocalImportUsage]


def test_main_script_entry_point(mocker: MockerFixture, test_file: str, mock_metadata: TrackMetadata) -> None:
    """Test the main entry point when running as a script.

    Args:
        mocker: Pytest mocker fixture.
        test_file: Path to test file.
        mock_metadata: Mock metadata fixture.
    """
    # Mock sys.argv to provide required arguments
    _ = mocker.patch("sys.argv", ["omym", test_file])

    # Mock file processing
    mock_processor = mocker.patch("omym.ui.cli.commands.executor.MusicProcessor")
    mock_instance = mock_processor.return_value
    mock_instance.process_file.return_value = ProcessResult(
        source_path=Path(test_file),
        target_path=Path("Artist/Album/01 - Test Track.mp3"),
        success=True,
        metadata=mock_metadata,
        artist_id=None,
    )

    # Import and execute the module
    import omym.main as main_module

    if hasattr(main_module, "__main_block__"):
        main_block: Callable[[], Any] = getattr(main_module, "__main_block__")
        main_block()
    else:
        main_module.main()  # pyright: ignore[reportPrivateLocalImportUsage]


def test_main_module_import(mocker: MockerFixture, test_file: str) -> None:
    """Test importing the main module without running it.

    Args:
        mocker: Pytest mocker fixture.
        test_file: Path to test file.
    """
    # Mock sys.argv to provide required arguments
    _ = mocker.patch("sys.argv", ["omym", "process", test_file])

    # Import and use the module
    import omym.__main__ as main_module

    assert hasattr(main_module, "main")


def test_main_script_import(mocker: MockerFixture, test_file: str) -> None:
    """Test importing the main script without running it.

    Args:
        mocker: Pytest mocker fixture.
        test_file: Path to test file.
    """
    # Mock sys.argv to provide required arguments
    _ = mocker.patch("sys.argv", ["omym", "process", test_file])

    # Import and use the module
    import omym.main as main_module

    assert hasattr(main_module, "main")
