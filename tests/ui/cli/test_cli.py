"""Tests for CLI functionality."""

import shutil
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from omym.features.metadata import ProcessResult
from omym.features.metadata import TrackMetadata
from omym.features.restoration.domain.models import (
    CollisionPolicy,
    RestorePlanItem,
    RestoreResult,
)
from omym.ui.cli import CommandProcessor
from omym.ui.cli.args.options import RestoreArgs


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
    mock = mocker.patch("omym.application.services.organize_service.MusicProcessor")
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


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> MagicMock:
    """Create a mock logger.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MagicMock: Mock logger instance.
    """
    return mocker.patch("omym.ui.cli.cli.logger")


def test_process_single_file(test_dir: Path, mock_processor: MagicMock, mocker: MockerFixture) -> None:
    """Test processing a single file.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    _ = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Process single file
    test_file = test_dir / "test.mp3"
    CommandProcessor.process_command(['organize', str(test_file)])

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
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    mock_progress = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Setup mock progress display
    mock_progress_instance = mock_progress.return_value
    mock_progress_instance.run_with_service.return_value = [mock_processor.process_file.return_value]

    # Process directory
    CommandProcessor.process_command(['organize', str(test_dir)])

    # Verify
    assert mock_progress_instance.run_with_service.call_count == 1
    args, kwargs = mock_progress_instance.run_with_service.call_args
    # Third positional arg is directory
    assert args[2] == test_dir
    assert kwargs.get("interactive") is False
    mock_result.return_value.show_results.assert_called_once()
    mock_preview.return_value.show_preview.assert_not_called()


def test_dry_run_mode(test_dir: Path, mocker: MockerFixture) -> None:
    """Test dry-run mode.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock displays
    mock_preview = mocker.patch("omym.ui.cli.commands.executor.PreviewDisplay")
    _ = mocker.patch("omym.ui.cli.commands.executor.ProgressDisplay")
    mock_result = mocker.patch("omym.ui.cli.commands.executor.ResultDisplay")

    # Process in dry-run mode
    CommandProcessor.process_command(['organize', str(test_dir), '--dry-run'])

    # Verify
    mock_preview.return_value.show_preview.assert_called_once()
    mock_result.return_value.show_results.assert_not_called()


def test_error_handling(
    test_dir: Path, mock_processor: MagicMock, mock_logger: MagicMock, mocker: MockerFixture
) -> None:
    """Test error handling.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mock_logger: Mock logger fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock sys.exit
    mock_exit = mocker.patch("sys.exit")

    # Setup mock to raise an exception
    mock_processor.process_file.side_effect = Exception("Test error")

    # Process file (should catch exception)
    test_file = test_dir / "test.mp3"
    CommandProcessor.process_command(['organize', str(test_file)])

    # Verify
    mock_logger.error.assert_called_once_with("An unexpected error occurred: %s", "Test error")
    mock_exit.assert_called_once_with(1)


def test_keyboard_interrupt(
    test_dir: Path, mock_processor: MagicMock, mock_logger: MagicMock, mocker: MockerFixture
) -> None:
    """Test keyboard interrupt handling.

    Args:
        test_dir: Test directory fixture.
        mock_processor: Mock processor fixture.
        mock_logger: Mock logger fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock sys.exit
    mock_exit = mocker.patch("sys.exit")

    # Setup mock to raise KeyboardInterrupt
    mock_processor.process_file.side_effect = KeyboardInterrupt()

    # Process file (should catch KeyboardInterrupt)
    test_file = test_dir / "test.mp3"
    CommandProcessor.process_command(['organize', str(test_file)])

    # Verify
    mock_logger.info.assert_called_once_with("\nOperation cancelled by user")
    mock_exit.assert_called_once_with(130)


def test_restore_command_invocation(tmp_path: Path, mocker: MockerFixture) -> None:
    """Restore command should delegate to the restore command executor."""

    restore_args = RestoreArgs(
        command="restore",
        source_root=tmp_path,
        destination_root=None,
        dry_run=False,
        verbose=False,
        quiet=False,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
        purge_state=False,
    )

    plan_item = RestorePlanItem(
        file_hash="abc",
        source_path=tmp_path / "a",
        destination_path=tmp_path / "b",
    )
    restore_result = RestoreResult(plan=plan_item, moved=True)

    _ = mocker.patch("omym.ui.cli.cli.ArgumentParser.process_args", return_value=restore_args)
    restore_command = mocker.patch("omym.ui.cli.cli.RestoreCommand")
    restore_command.return_value.execute.return_value = [restore_result]

    CommandProcessor.process_command()

    restore_command.return_value.execute.assert_called_once()


def test_restore_command_failure_exit(tmp_path: Path, mocker: MockerFixture) -> None:
    """Restore failures should trigger a non-zero exit code."""

    restore_args = RestoreArgs(
        command="restore",
        source_root=tmp_path,
        destination_root=None,
        dry_run=False,
        verbose=False,
        quiet=False,
        collision_policy=CollisionPolicy.ABORT,
        backup_suffix=".bak",
        continue_on_error=False,
        limit=None,
        purge_state=False,
    )
    plan_item = RestorePlanItem(
        file_hash="abc",
        source_path=tmp_path / "a",
        destination_path=tmp_path / "b",
    )
    restore_result = RestoreResult(plan=plan_item, moved=False, message="failure")

    _ = mocker.patch("omym.ui.cli.cli.ArgumentParser.process_args", return_value=restore_args)
    restore_command = mocker.patch("omym.ui.cli.cli.RestoreCommand")
    restore_command.return_value.execute.return_value = [restore_result]
    mock_exit = mocker.patch("sys.exit")

    CommandProcessor.process_command()

    mock_exit.assert_called_once_with(1)
