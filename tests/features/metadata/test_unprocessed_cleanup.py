"""Tests for unprocessed cleanup helpers using filesystem ports."""

from __future__ import annotations

from pathlib import Path

from pytest_mock import MockerFixture

from omym.config.settings import UNPROCESSED_DIR_NAME
from omym.features.metadata.usecases.ports import FilesystemPort
from omym.features.metadata.usecases.cleanup.unprocessed_cleanup import relocate_unprocessed_files


def test_relocate_unprocessed_files_invokes_filesystem_port(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """relocate_unprocessed_files should ensure directories and cleanup via the port."""

    source = tmp_path / "album" / "track.mp3"
    source.parent.mkdir(parents=True)
    _ = source.write_text("dummy")

    filesystem = mocker.create_autospec(FilesystemPort, instance=True)

    def ensure_parent(destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination.parent

    filesystem.ensure_parent_directory.side_effect = ensure_parent
    filesystem.remove_empty_directories.return_value = None

    moves = relocate_unprocessed_files(
        tmp_path,
        [source],
        unprocessed_dir_name=UNPROCESSED_DIR_NAME,
        dry_run=False,
        filesystem=filesystem,
    )

    destination = tmp_path / UNPROCESSED_DIR_NAME / "album" / "track.mp3"
    assert moves == [(source, destination)]
    assert destination.exists()
    assert not source.exists()

    filesystem.ensure_parent_directory.assert_called_once_with(destination)
    filesystem.remove_empty_directories.assert_called_once_with(tmp_path)
