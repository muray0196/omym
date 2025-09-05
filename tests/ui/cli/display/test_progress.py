"""Tests for progress display functionality."""

from collections.abc import Generator
from pathlib import Path
import tempfile
import pytest
from pytest_mock import MockerFixture

from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.metadata.music_file_processor import ProcessResult, MusicProcessor
from omym.ui.cli.display.progress import ProgressDisplay


@pytest.fixture
def test_dir() -> Generator[Path, None, None]:
    """Create a temporary test directory with test files.

    Yields:
        Path to test directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create test files
        (temp_path / "test1.mp3").touch()
        (temp_path / "test2.mp3").touch()
        yield temp_path


def test_process_files_with_progress(mocker: MockerFixture) -> None:
    """Test processing files with progress display."""
    # Mock Progress
    mock_progress = mocker.patch("omym.ui.cli.display.progress.Progress")
    mock_progress_instance = mock_progress.return_value.__enter__.return_value

    # Create test files
    test_dir = Path("test_music")
    test_files = [
        test_dir / "test1.mp3",
        test_dir / "test2.mp3",
    ]

    # Mock processor
    mock_processor = mocker.Mock(spec=MusicProcessor)
    metadata = TrackMetadata(
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        genre="Test Genre",
        year=2024,
        track_number=1,
        track_total=10,
        disc_number=1,
        disc_total=1,
        file_extension=".mp3",
    )
    mock_processor.process_file.return_value = ProcessResult(
        source_path=Path("test.mp3"),
        target_path=Path("Artist/Album/01 - Test Track.mp3"),
        success=True,
        metadata=metadata,
        artist_id=None,
    )

    # Mock Path.rglob
    _ = mocker.patch.object(Path, "rglob", return_value=test_files)
    _ = mocker.patch.object(Path, "is_file", return_value=True)

    # Process files
    display = ProgressDisplay()
    results = display.process_files_with_progress(mock_processor, test_dir)

    # Verify progress display
    mock_progress_instance.add_task.assert_called_once_with("[cyan]Processing files...", total=2)
    assert mock_progress_instance.update.call_count >= 2
    assert len(results) == 2
    assert all(result.success for result in results)


def test_process_files_with_progress_interactive(mocker: MockerFixture) -> None:
    """Test processing files with progress display in interactive mode."""
    # Mock Progress
    mock_progress = mocker.patch("omym.ui.cli.display.progress.Progress")
    mock_progress_instance = mock_progress.return_value.__enter__.return_value

    # Create test files
    test_dir = Path("test_music")
    test_files = [
        test_dir / "test1.mp3",
        test_dir / "test2.mp3",
    ]

    # Mock processor with error
    mock_processor = mocker.Mock(spec=MusicProcessor)
    mock_processor.process_file.return_value = ProcessResult(
        source_path=Path("test.mp3"),
        target_path=None,
        success=False,
        error_message="Test error",
        metadata=None,
        artist_id=None,
    )

    # Mock Path.rglob
    _ = mocker.patch.object(Path, "rglob", return_value=test_files)
    _ = mocker.patch.object(Path, "is_file", return_value=True)

    # Process files in interactive mode
    display = ProgressDisplay()
    results = display.process_files_with_progress(mock_processor, test_dir, interactive=True)

    # Verify progress display
    mock_progress_instance.add_task.assert_called_once_with("[cyan]Processing files...", total=2)
    assert mock_progress_instance.update.call_count >= 2
    assert len(results) == 2
    assert all(not result.success for result in results)
