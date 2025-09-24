"""Tests for application service that orchestrates organizing.

These tests verify that the service constructs a MusicProcessor and delegates
calls appropriately. Infra details are mocked so tests remain fast and stable.
"""

import logging
import sqlite3
from pathlib import Path

from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from omym.application.services.organize_service import (
    OrganizeMusicService,
    OrganizeRequest,
)
from omym.features.metadata import ProcessResult


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


def test_build_processor_warns_and_continues_on_cache_clear_failure(
    caplog: LogCaptureFixture, mocker: MockerFixture
) -> None:
    """build_processor should warn and continue when cache cleanup fails."""
    service = OrganizeMusicService()

    processor_mock = mocker.Mock()
    processor_mock.artist_dao = mocker.Mock()
    processor_mock.artist_dao.clear_cache.side_effect = sqlite3.OperationalError(
        "artist cache locked"
    )
    conn = mocker.Mock(name="conn")
    processor_mock.db_manager = mocker.Mock(conn=conn)

    _ = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor",
        return_value=processor_mock,
    )

    maintenance_cls = mocker.patch(
        "omym.application.services.organize_service.MaintenanceDAO"
    )
    maintenance_instance = maintenance_cls.return_value
    maintenance_instance.clear_all.side_effect = sqlite3.OperationalError(
        "maintenance clearing failed"
    )

    caplog.set_level(logging.WARNING, logger="omym")

    request = OrganizeRequest(
        base_path=Path("."),
        dry_run=False,
        clear_artist_cache=True,
        clear_cache=True,
    )

    result = service.build_processor(request)

    assert result is processor_mock
    processor_mock.artist_dao.clear_cache.assert_called_once_with()
    maintenance_cls.assert_called_once_with(conn)

    warning_messages = [
        record.message for record in caplog.records if record.levelno == logging.WARNING
    ]
    assert any("artist_dao.clear_cache()" in message for message in warning_messages)
    assert any("MaintenanceDAO.clear_all()" in message for message in warning_messages)


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
