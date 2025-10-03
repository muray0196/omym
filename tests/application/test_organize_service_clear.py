"""Tests for maintenance flags in OrganizeMusicService.

Focus on verifying delegation to DAOs rather than DB effects.
"""

from pathlib import Path
from pytest_mock import MockerFixture

from omym.application.services.organize_service import (
    OrganizeMusicService,
    OrganizeRequest,
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

    proc_instance = mocker.MagicMock()

    def processor_factory(*_: object, **kwargs: object) -> object:
        proc_instance.db_manager = kwargs["db_manager"]
        proc_instance.artist_dao = kwargs["artist_cache"]
        return proc_instance

    mocked_proc = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor",
        side_effect=processor_factory,
    )

    # Patch MaintenanceDAO
    mocked_maint = mocker.patch("omym.application.services.organize_service.MaintenanceDAO")
    maint_instance = mocked_maint.return_value

    service = OrganizeMusicService()

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

    proc_instance = mocker.MagicMock()

    def processor_factory(*_: object, **kwargs: object) -> object:
        proc_instance.db_manager = kwargs["db_manager"]
        proc_instance.artist_dao = kwargs["artist_cache"]
        return proc_instance

    _ = mocker.patch(
        "omym.application.services.organize_service.MusicProcessor",
        side_effect=processor_factory,
    )

    service = OrganizeMusicService()

    req = OrganizeRequest(base_path=Path("."), dry_run=True, clear_artist_cache=True)
    _ = service.build_processor(req)

    _ = artist_cache.clear_cache.assert_called_once()

