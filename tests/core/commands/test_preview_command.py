"""Tests for preview operations."""

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from omym.core.commands.preview_command import format_text_output, format_json_output, preview_files
from omym.core.path.path_generator import PathInfo


@pytest.fixture
def path_infos() -> list[PathInfo]:
    """Create test path information.

    Returns:
        list[PathInfo]: List of test path information objects.
    """
    return [
        PathInfo(
            file_hash="hash1",
            relative_path=Path("artist1/album1/track1.mp3"),
            warnings=[],
        ),
        PathInfo(
            file_hash="hash2",
            relative_path=Path("artist2/album2/track2.mp3"),
            warnings=["Warning 1", "Warning 2"],
        ),
    ]


def test_format_text_output(path_infos: list[PathInfo]) -> None:
    """Test text output formatting.

    Args:
        path_infos: Test path information fixture.
    """
    output = format_text_output(path_infos)
    expected = (
        "hash1: artist1/album1/track1.mp3\n"
        "hash2: artist2/album2/track2.mp3\n  Warnings: Warning 1, Warning 2"
    )
    assert output == expected


def test_format_json_output(path_infos: list[PathInfo]) -> None:
    """Test JSON output formatting.

    Args:
        path_infos: Test path information fixture.
    """
    output = format_json_output(path_infos)
    data = json.loads(output)
    assert len(data) == 2
    assert data[0] == {
        "file_hash": "hash1",
        "relative_path": "artist1/album1/track1.mp3",
        "warnings": [],
    }
    assert data[1] == {
        "file_hash": "hash2",
        "relative_path": "artist2/album2/track2.mp3",
        "warnings": ["Warning 1", "Warning 2"],
    }


def test_preview_single_file(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test previewing a single file.

    Args:
        tmp_path: Temporary directory path fixture.
        mocker: Pytest mocker fixture.
    """
    # Create test file
    test_file = tmp_path / "test.mp3"
    test_file.touch()

    # Mock database manager and components
    mock_db = mocker.patch("omym.core.commands.preview_command.DatabaseManager")
    mock_instance = mock_db.return_value.__enter__.return_value
    mock_instance.conn = True

    # Mock filter DAO
    mock_filter = mocker.patch("omym.core.commands.preview_command.FilterDAO")
    mock_filter_instance = mock_filter.return_value
    mock_filter_instance.get_hierarchies.return_value = []

    # Mock music grouper
    mock_grouper = mocker.patch("omym.core.commands.preview_command.MusicGrouper")
    mock_grouper_instance = mock_grouper.return_value
    mock_grouper_instance.group_by_path_format.return_value = {"hash1": {"file": str(test_file)}}

    # Mock path generator
    mock_generator = mocker.patch("omym.core.commands.preview_command.PathGenerator")
    mock_generator_instance = mock_generator.return_value
    mock_generator_instance.generate_paths.return_value = [
        PathInfo(
            file_hash="hash1",
            relative_path=Path("artist/album/track.mp3"),
            warnings=[],
        )
    ]

    # Run preview
    result = preview_files(test_file, "artist/{artist}/album/{album}", output_format="json")
    assert result == 0

    # Verify mocks
    mock_filter_instance.insert_hierarchy.assert_has_calls([
        mocker.call("artist", priority=0),
        mocker.call("{artist}", priority=0),
        mocker.call("album", priority=0),
        mocker.call("{album}", priority=0),
    ])
    mock_grouper_instance.group_by_path_format.assert_called_once_with(
        [test_file], "artist/{artist}/album/{album}"
    )
    mock_generator_instance.generate_paths.assert_called_once()


def test_preview_directory(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test previewing a directory.

    Args:
        tmp_path: Temporary directory path fixture.
        mocker: Pytest mocker fixture.
    """
    # Create test files
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    test_files = [
        music_dir / "test1.mp3",
        music_dir / "test2.mp3",
    ]
    for file in test_files:
        file.touch()

    # Mock database manager and components
    mock_db = mocker.patch("omym.core.commands.preview_command.DatabaseManager")
    mock_instance = mock_db.return_value.__enter__.return_value
    mock_instance.conn = True

    # Mock filter DAO
    mock_filter = mocker.patch("omym.core.commands.preview_command.FilterDAO")
    mock_filter_instance = mock_filter.return_value
    mock_filter_instance.get_hierarchies.return_value = []

    # Mock music grouper
    mock_grouper = mocker.patch("omym.core.commands.preview_command.MusicGrouper")
    mock_grouper_instance = mock_grouper.return_value
    mock_grouper_instance.group_by_path_format.return_value = {
        "hash1": {"file": str(test_files[0])},
        "hash2": {"file": str(test_files[1])},
    }

    # Mock path generator
    mock_generator = mocker.patch("omym.core.commands.preview_command.PathGenerator")
    mock_generator_instance = mock_generator.return_value
    mock_generator_instance.generate_paths.return_value = [
        PathInfo(
            file_hash="hash1",
            relative_path=Path("artist1/album1/track1.mp3"),
            warnings=[],
        ),
        PathInfo(
            file_hash="hash2",
            relative_path=Path("artist2/album2/track2.mp3"),
            warnings=["Warning"],
        ),
    ]

    # Run preview
    result = preview_files(music_dir, "artist/{artist}/album/{album}", output_format="json")
    assert result == 0

    # Verify mocks
    mock_filter_instance.insert_hierarchy.assert_has_calls([
        mocker.call("artist", priority=0),
        mocker.call("{artist}", priority=0),
        mocker.call("album", priority=0),
        mocker.call("{album}", priority=0),
    ])
    mock_grouper_instance.group_by_path_format.assert_called_once_with(
        test_files, "artist/{artist}/album/{album}"
    )
    mock_generator_instance.generate_paths.assert_called_once()


def test_preview_database_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test preview with database connection error.

    Args:
        tmp_path: Temporary directory path fixture.
        mocker: Pytest mocker fixture.
    """
    # Create test file
    test_file = tmp_path / "test.mp3"
    test_file.touch()

    # Mock database manager with no connection
    mock_db = mocker.patch("omym.core.commands.preview_command.DatabaseManager")
    mock_instance = mock_db.return_value.__enter__.return_value
    mock_instance.conn = None

    # Run preview
    result = preview_files(test_file, "artist/{artist}/album/{album}")
    assert result == 1


def test_preview_processing_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test preview with processing error.

    Args:
        tmp_path: Temporary directory path fixture.
        mocker: Pytest mocker fixture.
    """
    # Create test file
    test_file = tmp_path / "test.mp3"
    test_file.touch()

    # Mock database manager
    mock_db = mocker.patch("omym.core.commands.preview_command.DatabaseManager")
    mock_instance = mock_db.return_value.__enter__.return_value
    mock_instance.conn = True

    # Mock filter DAO that raises an error
    mock_filter = mocker.patch("omym.core.commands.preview_command.FilterDAO")
    mock_filter_instance = mock_filter.return_value
    mock_filter_instance.get_hierarchies.side_effect = Exception("Test error")

    # Run preview
    result = preview_files(test_file, "artist/{artist}/album/{album}")
    assert result == 1 