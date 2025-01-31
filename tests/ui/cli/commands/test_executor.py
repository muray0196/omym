"""Tests for command execution."""

import pytest
from pathlib import Path
from collections.abc import Generator
import shutil
from pytest_mock import MockerFixture
from typing import Any

from omym.core.metadata.track_metadata import TrackMetadata
from omym.core.metadata.music_file_processor import ProcessResult, MusicProcessor
from omym.ui.cli.args.options import Args
from omym.ui.cli.commands import FileCommand, DirectoryCommand
from omym.ui.cli.display import PreviewDisplay, ProgressDisplay, ResultDisplay


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
def test_args(test_dir: Path) -> Args:
    """Create test arguments.

    Args:
        test_dir: Test directory fixture.

    Returns:
        Args: Test arguments.
    """
    return Args(
        music_path=test_dir,
        target_path=test_dir,
        dry_run=False,
        verbose=False,
        quiet=False,
        force=False,
        interactive=False,
        config_path=None,
        show_db=False,
    )


@pytest.fixture
def mock_processor(mocker: MockerFixture) -> MusicProcessor:
    """Create a mock processor.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MusicProcessor: Mock processor instance.
    """
    mock = mocker.patch("omym.ui.cli.commands.executor.MusicProcessor")
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
        file_extension=".mp3",
    )

    mock_instance.process_file.return_value = ProcessResult(
        source_path=Path("test.mp3"),
        target_path=Path("Artist/Album/01 - Test Track.mp3"),
        success=True,
        metadata=metadata,
        artist_id=None,
    )

    return mock_instance


def test_file_command(test_args: Args, mock_processor: MockerFixture, mocker: MockerFixture) -> None:
    """Test file command execution.

    Args:
        test_args: Test arguments fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Create and execute command
    command = FileCommand(test_args)
    results = command.execute()

    # Verify
    assert len(results) == 1
    mock_processor.process_file.assert_called_once_with(test_args.music_path)
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_directory_command(test_args: Args, mock_processor: MockerFixture, mocker: MockerFixture) -> None:
    """Test directory command execution.

    Args:
        test_args: Test arguments fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Setup mock progress display
    mock_progress_instance = mock_progress.return_value
    mock_progress_instance.process_files_with_progress.return_value = [mock_processor.process_file.return_value]

    # Create and execute command
    command = DirectoryCommand(test_args)
    results = command.execute()

    # Verify
    assert len(results) == 1
    mock_progress_instance.process_files_with_progress.assert_called_once_with(
        mock_processor, test_args.music_path, interactive=test_args.interactive
    )
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_dry_run_mode(test_args: Args, mock_processor: MockerFixture, mocker: MockerFixture) -> None:
    """Test command execution in dry-run mode.

    Args:
        test_args: Test arguments fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Enable dry-run mode
    test_args.dry_run = True

    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Create and execute command
    command = FileCommand(test_args)
    results = command.execute()

    # Verify
    assert len(results) == 1
    mock_preview.return_value.show_preview.assert_called_once()
    mock_result.return_value.show_results.assert_not_called()


def test_file_command_error(test_args: Args, mock_processor: MusicProcessor, mocker: MockerFixture) -> None:
    """Test file command error handling.

    Args:
        test_args: Test arguments fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Setup error result
    mock_processor.process_file.return_value = ProcessResult(
        source_path=Path("test.mp3"), target_path=None, success=False, metadata=None, artist_id=None
    )

    # Create and execute command
    command = FileCommand(test_args)
    results = command.execute()

    # Verify
    assert len(results) == 1
    assert not results[0].success
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_directory_command_interactive(test_args: Args, mock_processor: MusicProcessor, mocker: MockerFixture) -> None:
    """Test directory command in interactive mode.

    Args:
        test_args: Test arguments fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Enable interactive mode
    test_args.interactive = True

    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Setup mock progress display
    mock_progress_instance = mock_progress.return_value
    mock_progress_instance.process_files_with_progress.return_value = [mock_processor.process_file.return_value]

    # Create and execute command
    command = DirectoryCommand(test_args)
    results = command.execute()

    # Verify
    assert len(results) == 1
    mock_progress_instance.process_files_with_progress.assert_called_once_with(
        mock_processor, test_args.music_path, interactive=True
    )
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_quiet_mode(test_args: Args, mock_processor: MusicProcessor, mocker: MockerFixture) -> None:
    """Test command execution in quiet mode.

    Args:
        test_args: Test arguments fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Enable quiet mode
    test_args.quiet = True

    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Create and execute command
    command = FileCommand(test_args)
    results = command.execute()

    # Verify
    assert len(results) == 1
    mock_result.return_value.show_results.assert_called_once_with(results, quiet=True)
    mock_preview.return_value.show_preview.assert_not_called()
