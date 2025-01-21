"""Tests for CLI functionality."""

from pathlib import Path
from pytest_mock import MockerFixture

from omym.ui.cli import process_command


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

    # Run CLI with music_path argument
    args = [str(test_file)]
    process_command(args)

    # Verify
    mock_processor.assert_called_once_with(base_path=test_file.parent, dry_run=False)
    mock_instance.process_file.assert_called_once_with(test_file)


def test_process_with_target(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test processing with target directory.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    # Create test directories and file
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"
    (source_dir / "test.mp3").touch()

    # Setup mock
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_progress.return_value = []

    # Run CLI
    args = [str(source_dir), "--target", str(target_dir)]
    process_command(args)

    # Verify
    mock_processor.assert_called_once_with(base_path=target_dir, dry_run=False)
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=False,
    )


def test_process_directory(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test processing a directory.

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
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_progress.return_value = []

    # Run CLI with quiet mode to avoid stdin interaction
    args = [str(source_dir), "--quiet"]
    process_command(args)

    # Verify
    mock_processor.assert_called_once_with(base_path=source_dir, dry_run=False)
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=False,
    )


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
    args = [str(source_dir), "--verbose"]
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
    args = [str(source_dir), "--quiet"]
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
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_progress.return_value = []

    # Run CLI with force flag
    args = [str(source_dir), "--force"]
    process_command(args)

    # Verify process_files_with_progress was used with interactive=False
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=False,
    )


def test_explicit_interactive_mode(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test interactive mode is enabled when explicitly requested.

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

    # Run CLI with interactive flag
    args = [str(source_dir), "--interactive"]
    process_command(args)

    # Verify interactive mode was used when explicitly requested
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=True,
    )


def test_default_non_interactive_mode(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test that non-interactive is the default mode.

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

    # Run CLI without any mode flags
    args = [str(source_dir)]
    process_command(args)

    # Verify non-interactive mode is the default
    mock_progress.assert_called_once_with(
        mock_processor.return_value,
        source_dir,
        interactive=False,
    )


def test_dry_run(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test dry run option.

    Args:
        tmp_path: Temporary directory path fixture
        mocker: Pytest mocker fixture
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Setup mocks
    mock_processor = mocker.patch("omym.ui.cli.MusicProcessor")
    mock_progress = mocker.patch("omym.ui.cli.process_files_with_progress")
    mock_preview = mocker.patch("omym.ui.cli.display_preview")
    mock_progress.return_value = []

    # Run CLI with dry-run flag
    args = [str(source_dir), "--dry-run"]
    process_command(args)

    # Verify
    mock_processor.assert_called_once_with(base_path=source_dir, dry_run=True)
    mock_preview.assert_called_once_with([], mock_processor.return_value.base_path, show_db=False)
