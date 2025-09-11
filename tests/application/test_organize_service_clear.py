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
    service = OrganizeMusicService()

    # Patch MusicProcessor to expose a db_manager with a connection
    mocked_proc = mocker.patch("omym.application.services.organize_service.MusicProcessor")
    proc_instance = mocked_proc.return_value
    db_manager = mocker.MagicMock()
    db_manager.conn = object()  # sentinel non-None
    proc_instance.db_manager = db_manager

    # Patch MaintenanceDAO
    mocked_maint = mocker.patch("omym.application.services.organize_service.MaintenanceDAO")
    maint_instance = mocked_maint.return_value

    req = OrganizeRequest(base_path=Path("."), dry_run=True, clear_cache=True)
    _ = service.build_processor(req)

    mocked_maint.assert_called_once()
    maint_instance.clear_all.assert_called_once()


def test_clear_artist_cache_uses_artist_dao(mocker: MockerFixture) -> None:
    """When clear_artist_cache=True, service should call ArtistCacheDAO.clear_cache()."""
    service = OrganizeMusicService()

    mocked_proc = mocker.patch("omym.application.services.organize_service.MusicProcessor")
    proc_instance = mocked_proc.return_value
    # Provide artist_dao with clear_cache()
    artist_dao = mocker.MagicMock()
    proc_instance.artist_dao = artist_dao

    req = OrganizeRequest(base_path=Path("."), dry_run=True, clear_artist_cache=True)
    _ = service.build_processor(req)

    artist_dao.clear_cache.assert_called_once()

