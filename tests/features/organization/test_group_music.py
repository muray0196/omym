"""Tests for music grouping behavior."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from omym.features.organization import MusicGrouper


@pytest.fixture
def music_grouper() -> MusicGrouper:
    """Create a music grouper instance."""
    return MusicGrouper()


def test_group_by_path_format_normalizes_components(
    tmp_path: Path,
    mocker: MockerFixture,
    music_grouper: MusicGrouper,
) -> None:
    """Ensure grouping handles duplicate separators, whitespace, and trailing slashes."""
    file_path = tmp_path / "song.flac"
    file_path.touch()

    metadata = SimpleNamespace(
        title="Song",
        artist="Artist",
        album="Album",
        album_artist="Album Artist",
        genre="Rock",
        year=2024,
        track_number=1,
        track_total=1,
        disc_number=1,
        disc_total=1,
    )

    _ = mocker.patch(
        "omym.features.metadata.usecases.track_metadata_extractor.MetadataExtractor.extract",
        return_value=metadata,
    )

    path_format = " AlbumArtist// Album / "
    result = music_grouper.group_by_path_format([file_path], path_format)

    assert result != {}
    assert str(file_path) in result
    assert result[str(file_path)]["album_artist"] == "Album Artist"
    assert result[str(file_path)]["album"] == "Album"
