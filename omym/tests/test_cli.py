"""Tests for CLI functionality."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_mock import MockerFixture

from omym.core.processor import ProcessResult
from omym.ui.cli import process_command

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


def test_process_single_file(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test processing a single file.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    # Create test file
    test_file = tmp_path / "test.mp3"
    test_file.touch()

    # Setup mock
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_instance = mock_processor.return_value
    mock_instance.process_file.return_value.success = True

    # Run CLI
    args = ["process", str(test_file)]
    process_command(args)

    # Verify
    mock_processor.assert_called_once()
    mock_instance.process_file.assert_called_once_with(test_file)


def test_organize_directory(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test organizing a directory.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    # Create test directory
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test.mp3").touch()

    # Setup mock
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_instance = mock_processor.return_value
    mock_instance.process_directory.return_value = []

    # Run CLI with quiet mode to avoid stdin interaction
    args = ["organize", str(source_dir), "--quiet"]
    process_command(args)

    # Verify
    mock_processor.assert_called_once()
    mock_instance.process_directory.assert_called_once_with(source_dir)


def test_verify_directory(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test verifying a directory.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test.mp3").touch()

    # Setup mock
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")

    # Run CLI with verify command in quiet mode
    args = ["verify", str(source_dir), "--quiet"]
    process_command(args)

    # Verify dry_run was set
    mock_processor.assert_called_once_with(
        base_path=source_dir,
        dry_run=True,
    )


def test_dry_run(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test dry run mode.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Setup mock
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")

    # Run CLI with dry-run
    args = ["organize", str(source_dir), "--dry-run"]
    process_command(args)

    # Verify dry-run was passed to processor and process_directory was used
    mock_processor.assert_called_once_with(
        base_path=source_dir,
        dry_run=True,
    )
    mock_processor.return_value.process_directory.assert_called_once_with(source_dir)


def test_verbose_logging(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test verbose logging option.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Setup mocks
    mock_logger = mocker.patch("omym.ui.cli.setup_logger")
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_progress.return_value = []

    # Run CLI with verbose flag
    args = ["organize", str(source_dir), "--verbose"]
    process_command(args)

    # Verify debug level was set
    mock_logger.assert_called_once_with(console_level=10)  # DEBUG level


def test_quiet_logging(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test quiet logging option.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Setup mock
    mock_logger = mocker.patch("omym.ui.cli.setup_logger")

    # Run CLI with quiet flag
    args = ["organize", str(source_dir), "--quiet"]
    process_command(args)

    # Verify error level was set
    mock_logger.assert_called_once_with(console_level=40)  # ERROR level


def test_force_option(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test force option disables interactive mode.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Setup mock
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_instance = mock_processor.return_value
    mock_instance.process_directory.return_value = []

    # Run CLI with force flag
    args = ["organize", str(source_dir), "--force"]
    process_command(args)

    # Verify process_directory was used directly
    mock_instance.process_directory.assert_called_once_with(source_dir)


def test_interactive_mode(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test interactive mode is enabled by default.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Setup mocks
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_progress.return_value = []

    # Run CLI without any flags
    args = ["organize", str(source_dir)]
    process_command(args)

    # Verify interactive mode was used
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=True,
    )


def test_invalid_path() -> None:
    """Test error when path doesn't exist."""
    with pytest.raises(SystemExit):
        process_command(["organize", "nonexistent/path"])


def test_wrong_path_type_process() -> None:
    """Test error when using directory for process command."""
    with pytest.raises(SystemExit):
        process_command(["process", "."])


def test_wrong_path_type_organize() -> None:
    """Test error when using file for organize command."""
    with pytest.raises(SystemExit):
        process_command(["organize", __file__])


def test_missing_command() -> None:
    """Test error when no command is provided."""
    with pytest.raises(SystemExit):
        process_command([])


def test_process_directory_interactive(
    tmp_path: Path, mocker: MockerFixture, capsys: "CaptureFixture[str]"
) -> None:
    """Test processing a directory in interactive mode.

    Args:
        tmp_path: Temporary directory path fixture.
        mocker: Pytest mocker fixture.
        capsys: Pytest capture fixture.
    """
    # Create test directory with files
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    test_file = source_dir / "test.mp3"
    test_file.touch()

    # Setup mocks
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_progress.return_value = [
        ProcessResult(
            source_path=test_file,
            target_path=tmp_path / "organized/test.mp3",
            success=True,
        )
    ]

    # Run CLI in interactive mode
    args = ["organize", str(source_dir)]
    process_command(args)

    # Verify interactive mode was used
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=True,
    )

    # Verify output
    captured = capsys.readouterr()
    assert "Processing Summary" in captured.out
    assert "Total files processed: 1" in captured.out
    assert "Successful: 1" in captured.out
    assert "Failed: 0" in captured.out
