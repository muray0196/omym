"""Tests for CLI functionality."""

import pytest
from pathlib import Path
from typing import Generator
import shutil
from pytest_mock import MockerFixture
from unittest.mock import MagicMock

from omym.core.metadata.music_file_processor import ProcessResult, TrackMetadata
from omym.ui.cli.cli import process_command


@pytest.fixture
def test_dir() -> Generator[Path, None, None]:
    """Create a temporary test directory.

    Yields:
        Path to test directory.
    """
    test_path = Path("test_music")
    test_path.mkdir(exist_ok=True)
    test_file = test_path / "test.mp3"
    test_file.touch()
    yield test_path
    # Cleanup
    if test_path.exists():
        shutil.rmtree(test_path)


@pytest.fixture
def mock_processor(mocker: MockerFixture) -> MagicMock:
    """Create a mock processor.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MagicMock: Mock processor instance.
    """
    mock = mocker.patch("omym.ui.cli.cli.MusicProcessor")
    mock_instance = mock.return_value

    # Setup mock process_file method
    metadata = TrackMetadata(
        title="Test Track",
        artist="Artist",
        album="Album",
        genre="Genre",
        year=2024,
        track_number=1,
        track_total=10,
        disc_number=1,
        disc_total=1,
        file_extension=".mp3"
    )

    mock_instance.process_file.return_value = ProcessResult(
        source_path=Path("test.mp3"),
        target_path=Path("Artist/Album/01 - Test Track.mp3"),
        success=True,
        metadata=metadata,
        artist_id=None
    )

    return mock_instance


def test_process_single_file(test_dir: Path, mock_processor: MagicMock, mocker: MockerFixture) -> None:
    """Test processing a single file.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.cli.PreviewDisplay")
    mock_result = mocker.patch("omym.ui.cli.cli.ResultDisplay")
    mocker.patch("omym.ui.cli.cli.ProgressDisplay")

    # Process single file
    test_file = test_dir / "test.mp3"
    process_command([str(test_file)])

    # Verify
    mock_processor.process_file.assert_called_once_with(test_file)
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_process_directory(test_dir: Path, mock_processor: MagicMock, mocker: MockerFixture) -> None:
    """Test processing a directory.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.cli.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.cli.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.cli.ResultDisplay")

    # Setup mock progress display
    mock_progress_instance = mock_progress.return_value
    mock_progress_instance.process_files_with_progress.return_value = [
        mock_processor.process_file.return_value
    ]

    # Process directory
    process_command([str(test_dir)])

    # Verify
    mock_progress_instance.process_files_with_progress.assert_called_once_with(
        mock_processor,
        test_dir,
        interactive=False
    )
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_dry_run_mode(test_dir: Path, mock_processor: MagicMock, mocker: MockerFixture) -> None:
    """Test dry-run mode.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.cli.PreviewDisplay")
    mock_result = mocker.patch("omym.ui.cli.cli.ResultDisplay")
    mocker.patch("omym.ui.cli.cli.ProgressDisplay")

    # Process in dry-run mode
    process_command([str(test_dir), "--dry-run"])

    # Verify
    mock_preview.return_value.show_preview.assert_called_once()
    mock_result.return_value.show_results.assert_not_called()


def test_error_handling(test_dir: Path, mock_processor: MagicMock, mocker: MockerFixture) -> None:
    """Test error handling.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock sys.exit and logger
    mock_exit = mocker.patch("sys.exit")
    mock_logger = mocker.patch("omym.ui.cli.cli.logger")

    # Setup mock to raise an exception
    mock_processor.process_file.side_effect = Exception("Test error")

    # Process file (should catch exception)
    test_file = test_dir / "test.mp3"
    process_command([str(test_file)])

    # Verify
    mock_logger.error.assert_called_once()
    mock_exit.assert_called_once_with(1)


def test_keyboard_interrupt(test_dir: Path, mock_processor: MagicMock, mocker: MockerFixture) -> None:
    """Test keyboard interrupt handling.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock sys.exit and logger
    mock_exit = mocker.patch("sys.exit")
    mock_logger = mocker.patch("omym.ui.cli.cli.logger")

    # Setup mock to raise KeyboardInterrupt
    mock_processor.process_file.side_effect = KeyboardInterrupt()

    # Process file (should catch KeyboardInterrupt)
    test_file = test_dir / "test.mp3"
    process_command([str(test_file)])

    # Verify
    mock_logger.info.assert_called_once_with("\nOperation cancelled by user")
    mock_exit.assert_called_once_with(130) 