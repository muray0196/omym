"""Tests for application service that orchestrates organizing.

These tests verify that the service constructs a MusicProcessor and delegates
calls appropriately. Infra details are mocked so tests remain fast and stable.
"""

import logging
import sqlite3
from pathlib import Path
from typing import cast

from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from omym.application.services.organize_service import (
    OrganizeMusicService,
    OrganizeRequest,
)
from omym.features.metadata import ProcessResult
from omym.features.metadata.adapters import LocalFilesystemAdapter
from omym.features.metadata.usecases.ports import ArtistCachePort, RomanizationPort


def test_build_processor_constructs_music_processor(mocker: MockerFixture) -> None:
    """Service should construct a MusicProcessor with given parameters."""

    mock_db_cls = mocker.patch(
        "omym.application.services.organize_service.DatabaseManager"
    )
    db_instance = mock_db_cls.return_value
    db_instance.conn = None
    db_connection = mocker.Mock(name="conn")

    def connect_side_effect() -> None:
        db_instance.conn = db_connection

    db_instance.connect.side_effect = connect_side_effect

    mock_before_cls = mocker.patch(
        "omym.application.services.organize_service.ProcessingBeforeDAO"
    )
    before_instance = mock_before_cls.return_value

    mock_after_cls = mocker.patch(
        "omym.application.services.organize_service.ProcessingAfterDAO"
    )
    after_instance = mock_after_cls.return_value

    mock_preview_cls = mocker.patch(
        "omym.application.services.organize_service.ProcessingPreviewDAO"
    )
    preview_instance = mock_preview_cls.return_value

    mock_artist_cls = mocker.patch(
        "omym.application.services.organize_service.ArtistCacheDAO"
    )
    base_artist_instance = mock_artist_cls.return_value

    mock_dry_run_cls = mocker.patch(
        "omym.application.services.organize_service.DryRunArtistCacheAdapter"
    )
    dry_run_instance = mock_dry_run_cls.return_value

    romanization_port: RomanizationPort = mocker.create_autospec(RomanizationPort, instance=True)

    mocked_processor = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor"
    )

    service = OrganizeMusicService(romanization_port_factory=lambda: romanization_port)

    req = OrganizeRequest(base_path=Path("."), dry_run=True)
    _ = service.build_processor(req)

    _ = mock_db_cls.assert_called_once_with()
    _ = db_instance.connect.assert_called_once_with()
    _ = mock_before_cls.assert_called_once_with(db_connection)
    _ = mock_after_cls.assert_called_once_with(db_connection)
    _ = mock_preview_cls.assert_called_once_with(db_connection)
    _ = mock_artist_cls.assert_called_once_with(db_connection)
    _ = mock_dry_run_cls.assert_called_once_with(base_artist_instance)

    _ = mocked_processor.assert_called_once()
    kwargs = mocked_processor.call_args.kwargs
    assert kwargs.get("base_path") == Path(".")
    assert kwargs.get("dry_run") is True
    assert kwargs.get("db_manager") is db_instance
    assert kwargs.get("before_gateway") is before_instance
    assert kwargs.get("after_gateway") is after_instance
    assert kwargs.get("preview_cache") is preview_instance
    assert kwargs.get("artist_cache") is dry_run_instance
    assert kwargs.get("romanization_port") is romanization_port
    assert isinstance(kwargs.get("filesystem"), LocalFilesystemAdapter)


def test_build_processor_warns_and_continues_on_cache_clear_failure(
    caplog: LogCaptureFixture, mocker: MockerFixture
) -> None:
    """build_processor should warn and continue when cache cleanup fails."""
    processor_mock = mocker.Mock()
    conn = mocker.Mock(name="conn")
    db_manager = mocker.Mock(conn=conn)
    processor_mock.db_manager = db_manager

    base_artist = mocker.Mock()
    processor_mock.artist_dao = base_artist
    base_artist.clear_cache.side_effect = sqlite3.OperationalError("artist cache locked")

    _ = mocker.patch(
        "omym.application.services.organize_service.DatabaseManager",
        return_value=db_manager,
    )
    _ = mocker.patch(
        "omym.application.services.organize_service.ProcessingBeforeDAO"
    )
    _ = mocker.patch(
        "omym.application.services.organize_service.ProcessingAfterDAO"
    )
    _ = mocker.patch(
        "omym.application.services.organize_service.ProcessingPreviewDAO"
    )
    _ = mocker.patch(
        "omym.application.services.organize_service.ArtistCacheDAO",
        return_value=base_artist,
    )
    mock_dry_run = mocker.patch(
        "omym.application.services.organize_service.DryRunArtistCacheAdapter"
    )

    romanization_port: RomanizationPort = mocker.create_autospec(RomanizationPort, instance=True)

    def processor_factory(*_: object, **kwargs: object) -> object:
        romanization_port = cast(RomanizationPort, kwargs["romanization_port"])
        artist_cache = cast(ArtistCachePort, kwargs["artist_cache"])
        romanization_port.configure_cache(artist_cache)
        return processor_mock

    _ = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor",
        side_effect=processor_factory,
    )

    maintenance_cls = mocker.patch(
        "omym.application.services.organize_service.MaintenanceDAO"
    )
    maintenance_instance = maintenance_cls.return_value
    maintenance_instance.clear_all.side_effect = sqlite3.OperationalError(
        "maintenance clearing failed"
    )

    service = OrganizeMusicService(romanization_port_factory=lambda: romanization_port)

    caplog.set_level(logging.WARNING, logger="omym")

    request = OrganizeRequest(
        base_path=Path("."),
        dry_run=False,
        clear_artist_cache=True,
        clear_cache=True,
    )

    result = service.build_processor(request)

    assert result is processor_mock
    _ = processor_mock.artist_dao.clear_cache.assert_called_once_with()
    _ = maintenance_cls.assert_called_once_with(conn)
    mock_dry_run.assert_not_called()
    getattr(romanization_port, "configure_cache").assert_called_once_with(base_artist)

    warning_messages = [
        record.message for record in caplog.records if record.levelno == logging.WARNING
    ]
    assert any("artist_dao.clear_cache()" in message for message in warning_messages)
    assert any("MaintenanceDAO.clear_all()" in message for message in warning_messages)


def test_process_file_delegates(mocker: MockerFixture) -> None:
    """process_file should delegate to MusicProcessor.process_file()."""
    service = OrganizeMusicService()
    req = OrganizeRequest(base_path=Path("."), dry_run=True)

    processor = mocker.Mock()
    _ = mocker.patch.object(service, "build_processor", return_value=processor)
    processor.process_file.return_value = ProcessResult(source_path=Path("a.mp3"), success=True)

    res = service.process_file(req, Path("a.mp3"))
    assert res.success is True
    processor.process_file.assert_called_once()
