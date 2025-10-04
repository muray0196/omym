"""Summary: Ensure OrganizeMusicService maintenance flags trigger DAO calls.
Why: Guard against regressions where cache-clearing flags skip persistence layers."""

from pathlib import Path
from typing import cast
from pytest_mock import MockerFixture

from omym.application.services.organize_service import (
    OrganizeMusicService,
    OrganizeRequest,
)
from omym.features.metadata.usecases.ports import (
    ArtistCachePort,
    RenamerPorts,
    RomanizationPort,
)


def test_clear_cache_uses_maintenance_dao(mocker: MockerFixture) -> None:
    """When clear_cache=True, service should call MaintenanceDAO.clear_all()."""
    db_manager = mocker.MagicMock()
    db_manager.conn = object()
    artist_cache = mocker.MagicMock()

    mocked_db = mocker.patch(
        "omym.application.services.organize_service.DatabaseManager",
        return_value=db_manager,
    )
    mocked_before = mocker.patch(
        "omym.application.services.organize_service.ProcessingBeforeDAO"
    )
    mocked_after = mocker.patch(
        "omym.application.services.organize_service.ProcessingAfterDAO"
    )
    mocked_preview = mocker.patch(
        "omym.application.services.organize_service.ProcessingPreviewDAO"
    )
    mocked_artist = mocker.patch(
        "omym.application.services.organize_service.ArtistCacheDAO"
    )
    mocked_dry_run = mocker.patch(
        "omym.application.services.organize_service.DryRunArtistCacheAdapter",
        return_value=artist_cache,
    )

    romanization_port: RomanizationPort = mocker.create_autospec(RomanizationPort, instance=True)

    proc_instance = mocker.MagicMock()

    def processor_factory(*_: object, **kwargs: object) -> object:
        proc_instance.db_manager = kwargs["db_manager"]
        artist_cache_kw = cast(ArtistCachePort, kwargs["artist_cache"])
        proc_instance.artist_dao = artist_cache_kw
        romanization_port_kw = cast(RomanizationPort, kwargs["romanization_port"])
        romanization_port_kw.configure_cache(artist_cache_kw)
        proc_instance.romanization_port = romanization_port_kw
        renamer_ports_kw = cast(RenamerPorts, kwargs["renamer_ports"])
        assert renamer_ports_kw.file_name is not None
        return proc_instance

    mocked_proc = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor",
        side_effect=processor_factory,
    )

    # Patch MaintenanceDAO
    mocked_maint = mocker.patch("omym.application.services.organize_service.MaintenanceDAO")
    maint_instance = mocked_maint.return_value

    service = OrganizeMusicService(romanization_port_factory=lambda: romanization_port)

    req = OrganizeRequest(base_path=Path("."), dry_run=True, clear_cache=True)
    _ = service.build_processor(req)

    _ = mocked_db.assert_called_once_with()
    _ = mocked_before.assert_called_once()
    _ = mocked_after.assert_called_once()
    _ = mocked_preview.assert_called_once()
    _ = mocked_artist.assert_called_once()
    _ = mocked_dry_run.assert_called_once()
    _ = mocked_proc.assert_called_once()
    _ = mocked_maint.assert_called_once()
    _ = maint_instance.clear_all.assert_called_once()
    getattr(romanization_port, "configure_cache").assert_called_once_with(artist_cache)


def test_clear_artist_cache_uses_artist_dao(mocker: MockerFixture) -> None:
    """When clear_artist_cache=True, service should call ArtistCacheDAO.clear_cache()."""
    db_manager = mocker.MagicMock()
    db_manager.conn = object()
    artist_cache = mocker.MagicMock()

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
        return_value=artist_cache,
    )
    _ = mocker.patch(
        "omym.application.services.organize_service.DryRunArtistCacheAdapter",
        return_value=artist_cache,
    )

    romanization_port: RomanizationPort = mocker.create_autospec(RomanizationPort, instance=True)

    proc_instance = mocker.MagicMock()

    def processor_factory(*_: object, **kwargs: object) -> object:
        proc_instance.db_manager = kwargs["db_manager"]
        artist_cache_kw = cast(ArtistCachePort, kwargs["artist_cache"])
        proc_instance.artist_dao = artist_cache_kw
        romanization_port_kw = cast(RomanizationPort, kwargs["romanization_port"])
        romanization_port_kw.configure_cache(artist_cache_kw)
        proc_instance.romanization_port = romanization_port_kw
        renamer_ports_kw = cast(RenamerPorts, kwargs["renamer_ports"])
        assert renamer_ports_kw.directory is not None
        return proc_instance

    _ = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor",
        side_effect=processor_factory,
    )

    service = OrganizeMusicService(romanization_port_factory=lambda: romanization_port)

    req = OrganizeRequest(base_path=Path("."), dry_run=True, clear_artist_cache=True)
    _ = service.build_processor(req)

    _ = artist_cache.clear_cache.assert_called_once()
    getattr(romanization_port, "configure_cache").assert_called_once_with(artist_cache)

