"""Tests for command line argument parser."""

import logging
import shutil
import pytest
from pathlib import Path
from typing import Generator
from pytest_mock import MockerFixture

from omym.ui.cli.args.parser import create_parser, process_args


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


def test_create_parser() -> None:
    """Test argument parser creation."""
    parser = create_parser()
    
    # Test with minimum required arguments
    args = parser.parse_args(["test_path"])
    assert args.music_path == "test_path"
    assert not args.target
    assert not args.dry_run
    assert not args.verbose
    assert not args.quiet
    assert not args.force
    assert not args.interactive
    assert not args.config
    assert not args.db

    # Test with all arguments
    args = parser.parse_args([
        "test_path",
        "--target", "target_path",
        "--dry-run",
        "--verbose",
        "--force",
        "--interactive",
        "--config", "config.yaml",
        "--db"
    ])
    assert args.music_path == "test_path"
    assert args.target == "target_path"
    assert args.dry_run
    assert args.verbose
    assert args.force
    assert args.interactive
    assert args.config == "config.yaml"
    assert args.db


def test_process_args(test_dir: Path, mocker: MockerFixture) -> None:
    """Test argument processing.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock config and logger setup
    mock_config = mocker.patch("omym.ui.cli.args.parser.Config")
    mock_setup_logger = mocker.patch("omym.ui.cli.args.parser.setup_logger")

    # Test with minimum required arguments
    args = process_args([str(test_dir)])
    assert args.music_path == test_dir
    assert args.target_path == test_dir
    assert not args.dry_run
    assert not args.verbose
    assert not args.quiet
    assert not args.force
    assert not args.interactive
    assert args.config_path is None
    assert not args.show_db
    mock_setup_logger.assert_called_with(console_level=logging.INFO)
    mock_config.load.assert_called_once()

    # Test with all arguments
    target_path = test_dir / "target"
    config_path = test_dir / "config.yaml"
    args = process_args([
        str(test_dir),
        "--target", str(target_path),
        "--dry-run",
        "--verbose",
        "--force",
        "--interactive",
        "--config", str(config_path),
        "--db"
    ])
    assert args.music_path == test_dir
    assert args.target_path == target_path
    assert args.dry_run
    assert args.verbose
    assert args.force
    assert args.interactive
    assert args.config_path == config_path
    assert args.show_db
    mock_setup_logger.assert_called_with(console_level=logging.DEBUG)
    mock_config.load.assert_called_with(config_path)


def test_process_args_invalid_path(mocker: MockerFixture) -> None:
    """Test argument processing with invalid path.

    Args:
        mocker: Pytest mocker fixture.
    """
    # Mock logger and sys.exit
    mock_exit = mocker.patch("sys.exit")

    # Test with non-existent path
    process_args(["non_existent_path"])
    mock_exit.assert_called_once_with(1)


def test_process_args_quiet_mode(test_dir: Path, mocker: MockerFixture) -> None:
    """Test argument processing in quiet mode.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock setup_logger
    mock_setup_logger = mocker.patch("omym.ui.cli.args.parser.setup_logger")

    # Test with quiet mode
    args = process_args([str(test_dir), "--quiet"])
    assert args.quiet
    mock_setup_logger.assert_called_with(console_level=logging.ERROR) 