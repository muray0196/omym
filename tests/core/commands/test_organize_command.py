"""Tests for file organization operations."""

from pathlib import Path
from typing import Generator

import pytest
from pytest_mock import MockerFixture

from omym.core.commands.organize_command import organize_files


@pytest.fixture
def test_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a test directory with sample files.

    Args:
        tmp_path: Pytest temporary path fixture.

    Yields:
        Path: Path to the test directory.
    """
    # Create source directory
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create test files
    music_files = ["test1.mp3", "test2.mp3"]
    other_files = ["test.txt", "test.jpg"]

    for name in music_files + other_files:
        (source_dir / name).touch()

    yield source_dir


def test_organize_files_default_target(test_dir: Path, mocker: MockerFixture) -> None:
    """Test organizing files with default target directory.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock database operations
    mock_db = mocker.patch("omym.core.commands.organize_command.DatabaseManager")
    mock_conn = mocker.MagicMock()
    mock_db.return_value.__enter__.return_value.conn = mock_conn

    # Mock metadata extraction
    mock_metadata = mocker.patch("omym.core.metadata.music_file_processor.MetadataExtractor.extract")
    mock_metadata.return_value.album_artist = "Test Artist"
    mock_metadata.return_value.album = "Test Album"

    # Mock file operations
    mock_move = mocker.patch("shutil.move")

    # Call organize_files with default target_dir
    result = organize_files(test_dir, "AlbumArtist/Album")

    # Verify
    assert result == 0
    assert mock_move.call_count > 0  # Files were moved
    for call in mock_move.call_args_list:
        target_path = Path(call.args[1])
        assert target_path.is_relative_to(test_dir)  # Target paths are under source directory


def test_organize_files_custom_target(test_dir: Path, tmp_path: Path, mocker: MockerFixture) -> None:
    """Test organizing files with custom target directory.

    Args:
        test_dir: Test directory fixture.
        tmp_path: Pytest temporary path fixture.
        mocker: Pytest mocker fixture.
    """
    # Create custom target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Mock database operations
    mock_db = mocker.patch("omym.core.commands.organize_command.DatabaseManager")
    mock_conn = mocker.MagicMock()
    mock_db.return_value.__enter__.return_value.conn = mock_conn

    # Mock metadata extraction
    mock_metadata = mocker.patch("omym.core.metadata.music_file_processor.MetadataExtractor.extract")
    mock_metadata.return_value.album_artist = "Test Artist"
    mock_metadata.return_value.album = "Test Album"

    # Mock file operations
    mock_move = mocker.patch("shutil.move")

    # Call organize_files with custom target_dir
    result = organize_files(test_dir, "AlbumArtist/Album", target_dir=target_dir)

    # Verify
    assert result == 0
    assert mock_move.call_count > 0  # Files were moved
    for call in mock_move.call_args_list:
        target_path = Path(call.args[1])
        assert target_path.is_relative_to(target_dir)  # Target paths are under target directory


def test_organize_files_dry_run(test_dir: Path, mocker: MockerFixture) -> None:
    """Test organizing files in dry run mode.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock database operations
    mock_db = mocker.patch("omym.core.commands.organize_command.DatabaseManager")
    mock_conn = mocker.MagicMock()
    mock_db.return_value.__enter__.return_value.conn = mock_conn

    # Mock metadata extraction
    mock_metadata = mocker.patch("omym.core.metadata.music_file_processor.MetadataExtractor.extract")
    mock_metadata.return_value.album_artist = "Test Artist"
    mock_metadata.return_value.album = "Test Album"

    # Mock file operations
    mock_move = mocker.patch("shutil.move")

    # Mock logger
    mock_logger = mocker.MagicMock()
    mocker.patch("omym.core.commands.organize_command.logger", mock_logger)

    # Call organize_files in dry run mode
    result = organize_files(test_dir, "AlbumArtist/Album", dry_run=True)

    # Verify
    assert result == 0
    mock_move.assert_not_called()  # No files were moved
    assert mock_logger.info.call_count > 0  # Logged what would be done


def test_organize_files_force_overwrite(test_dir: Path, mocker: MockerFixture) -> None:
    """Test organizing files with force overwrite.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock database operations
    mock_db = mocker.patch("omym.core.commands.organize_command.DatabaseManager")
    mock_conn = mocker.MagicMock()
    mock_db.return_value.__enter__.return_value.conn = mock_conn

    # Mock metadata extraction
    mock_metadata = mocker.patch("omym.core.metadata.music_file_processor.MetadataExtractor.extract")
    mock_metadata.return_value.album_artist = "Test Artist"
    mock_metadata.return_value.album = "Test Album"

    # Mock file operations to simulate existing files
    def mock_exists(path: Path) -> bool:
        return True  # Simulate all target paths exist

    mocker.patch("pathlib.Path.exists", mock_exists)
    mock_move = mocker.patch("shutil.move")
    mock_unlink = mocker.patch("pathlib.Path.unlink")

    # Call organize_files with force overwrite
    result = organize_files(test_dir, "AlbumArtist/Album", force=True)

    # Verify
    assert result == 0
    assert mock_move.call_count > 0  # Files were moved
    assert mock_unlink.call_count > 0  # Existing files were removed


def test_organize_files_single_file(test_dir: Path, mocker: MockerFixture) -> None:
    """Test organizing a single file.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock database operations
    mock_db = mocker.patch("omym.core.commands.organize_command.DatabaseManager")
    mock_conn = mocker.MagicMock()
    mock_db.return_value.__enter__.return_value.conn = mock_conn

    # Mock metadata extraction
    mock_metadata = mocker.patch("omym.core.metadata.music_file_processor.MetadataExtractor.extract")
    mock_metadata.return_value.album_artist = "Test Artist"
    mock_metadata.return_value.album = "Test Album"

    # Mock file operations
    mock_move = mocker.patch("shutil.move")

    # Call organize_files with a single file
    single_file = test_dir / "test1.mp3"
    result = organize_files(single_file, "AlbumArtist/Album")

    # Verify
    assert result == 0
    assert mock_move.call_count == 1  # Only one file was moved 