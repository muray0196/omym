"""Tests for command line argument parser."""

import logging
import shutil
from argparse import Namespace
from collections.abc import Generator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from omym.ui.cli.args import ArgumentParser, OrganizeArgs, RestoreArgs
from omym.platform.logging import DEFAULT_LOG_FILE


@pytest.fixture()
def test_dir() -> Generator[Path, None, None]:
    """Create a temporary test directory."""

    test_path = Path("test_music")
    test_path.mkdir(exist_ok=True)
    test_file = test_path / "test.mp3"
    test_file.touch()
    yield test_path
    if test_path.exists():
        shutil.rmtree(test_path)


def test_create_parser() -> None:
    """Argument parser should expose expected subcommands and options."""

    parser = ArgumentParser.create_parser()

    organize_args: Namespace = parser.parse_args(["organize", "music"])
    assert organize_args.command == "organize"
    assert organize_args.music_path == "music"

    restore_args: Namespace = parser.parse_args(["restore", "organized"])
    assert restore_args.command == "restore"
    assert restore_args.source_root == "organized"

    all_flags = parser.parse_args(
        [
            "organize",
            "music",
            "--target",
            "target",
            "--dry-run",
            "--verbose",
            "--force",
            "--interactive",
            "--db",
            "--clear-artist-cache",
            "--clear-cache",
        ]
    )
    assert all_flags.dry_run and all_flags.verbose and all_flags.force
    assert all_flags.interactive and all_flags.db


def test_process_args_organize(test_dir: Path, mocker: MockerFixture) -> None:
    """Process organize arguments and coerce paths and logging levels."""

    mock_config = mocker.patch("omym.ui.cli.args.parser.Config")
    mock_setup_logger = mocker.patch("omym.ui.cli.args.parser.setup_logger")

    mock_config.load.return_value.log_file = None

    args = ArgumentParser.process_args(["organize", str(test_dir)])
    assert isinstance(args, OrganizeArgs)
    assert args.music_path == test_dir
    assert args.target_path == test_dir
    assert not args.dry_run
    assert mock_setup_logger.call_args.kwargs["console_level"] == logging.INFO
    assert mock_setup_logger.call_args.kwargs["log_file"] == DEFAULT_LOG_FILE
    mock_config.load.assert_called_once()

    target_path = test_dir / "target"
    mock_setup_logger.reset_mock()
    args = ArgumentParser.process_args(
        [
            "organize",
            str(test_dir),
            "--target",
            str(target_path),
            "--dry-run",
            "--verbose",
            "--force",
            "--interactive",
            "--db",
            "--clear-artist-cache",
            "--clear-cache",
        ]
    )
    assert isinstance(args, OrganizeArgs)
    assert args.target_path == target_path
    assert args.dry_run and args.verbose and args.force and args.interactive
    assert args.show_db and args.clear_artist_cache and args.clear_cache
    assert mock_setup_logger.call_args.kwargs["console_level"] == logging.DEBUG
    assert mock_setup_logger.call_args.kwargs["log_file"] == DEFAULT_LOG_FILE


def test_process_args_restore(test_dir: Path, mocker: MockerFixture) -> None:
    """Process restore arguments and enforce policies."""

    mock_config = mocker.patch("omym.ui.cli.args.parser.Config")
    mock_setup_logger = mocker.patch("omym.ui.cli.args.parser.setup_logger")
    custom_log_path = Path("/tmp/custom.log")
    mock_config.load.return_value.log_file = custom_log_path

    dest = test_dir / "restore_dest"
    args = ArgumentParser.process_args(
        [
            "restore",
            str(test_dir),
            "--destination-root",
            str(dest),
            "--collision-policy",
            "backup",
            "--backup-suffix",
            ".bak",
            "--limit",
            "5",
            "--continue-on-error",
            "--dry-run",
            "--quiet",
            "--purge-state",
        ]
    )

    assert isinstance(args, RestoreArgs)
    assert args.source_root == test_dir.resolve()
    assert args.destination_root == dest.resolve()
    assert args.collision_policy.value == "backup"
    assert args.limit == 5
    assert args.continue_on_error
    assert args.dry_run and args.quiet and args.purge_state
    assert mock_setup_logger.call_args.kwargs["console_level"] == logging.ERROR
    assert mock_setup_logger.call_args.kwargs["log_file"] == custom_log_path
    mock_config.load.assert_called_once()


def test_process_args_invalid_path(mocker: MockerFixture) -> None:
    """Invalid organize path should trigger an exit."""

    mock_exit = mocker.patch("sys.exit")
    _ = ArgumentParser.process_args(["organize", "non_existent_path"])
    mock_exit.assert_called_once_with(1)


def test_process_args_invalid_limit(test_dir: Path, mocker: MockerFixture) -> None:
    """Non-positive limits for restore should terminate parsing."""

    mock_exit = mocker.patch("sys.exit")
    _ = ArgumentParser.process_args(["restore", str(test_dir), "--limit", "0"])
    mock_exit.assert_called_once_with(1)
