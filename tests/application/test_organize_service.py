"""Tests for application service that orchestrates organizing.

These tests verify that the service constructs a MusicProcessor and delegates
calls appropriately. Infra details are mocked so tests remain fast and stable.
"""

from pathlib import Path
from pytest_mock import MockerFixture

from omym.application.services.organize_service import (
    OrganizeMusicService,
    OrganizeRequest,
)
from omym.domain.metadata.music_file_processor import ProcessResult


def test_build_processor_constructs_music_processor(mocker: MockerFixture) -> None:
    """Service should construct a MusicProcessor with given parameters."""
    service = OrganizeMusicService()

    # Patch MusicProcessor to observe construction
    mocked = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor"
    )
    _ = mocked.return_value

    req = OrganizeRequest(base_path=Path("."), dry_run=True)
    _ = service.build_processor(req)

    mocked.assert_called_once()
    kwargs = mocked.call_args.kwargs
    assert kwargs.get("base_path") == Path(".")
    assert kwargs.get("dry_run") is True


def test_process_file_delegates(mocker: MockerFixture) -> None:
    """process_file should delegate to MusicProcessor.process_file()."""
    service = OrganizeMusicService()
    req = OrganizeRequest(base_path=Path("."), dry_run=True)

    # Mock processor
    mocked_proc = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor"
    )
    instance = mocked_proc.return_value
    instance.process_file.return_value = ProcessResult(source_path=Path("a.mp3"), success=True)

    res = service.process_file(req, Path("a.mp3"))
    assert res.success is True
    instance.process_file.assert_called_once()

