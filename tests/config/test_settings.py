"""Tests for settings module behavior."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isolate config paths to a temporary repository root."""
    # Create repo marker so _detect_repo_root resolves to tmp_path
    _ = (tmp_path / "pyproject.toml").write_text("[project]\nname='tmp'\n")

    import omym.config.paths as paths

    def _fake_detect_repo_root(_start: Path | None = None) -> Path:
        return tmp_path

    monkeypatch.setattr(paths, "_detect_repo_root", _fake_detect_repo_root, raising=True)

    # Reset config singleton before reloading settings
    import omym.config.config as config_module

    config_module.Config._instance = None  # pyright: ignore[reportPrivateUsage]
    config_module.Config._loaded_from = None  # pyright: ignore[reportPrivateUsage]
    config_module.config = config_module.Config.load()

    yield

    # Clean up singletons after test
    config_module.Config._instance = None  # pyright: ignore[reportPrivateUsage]
    config_module.Config._loaded_from = None  # pyright: ignore[reportPrivateUsage]


def test_use_mb_romanization_defaults_true(
    isolated_environment: None,
) -> None:
    """Default configuration enables MusicBrainz romanization."""
    _ = isolated_environment

    import omym.config.settings as settings

    reloaded = importlib.reload(settings)

    assert reloaded.USE_MB_ROMANIZATION is True


def test_musicbrainz_identity_uses_config_defaults(
    isolated_environment: None,
) -> None:
    """MusicBrainz identity derives from config values."""

    _ = isolated_environment

    from omym.config.config import config as app_config

    app_config.use_mb_romanization = False
    app_config.mb_app_name = "custom-app"
    app_config.mb_app_version = "9.9.9"
    app_config.mb_contact = "mailto:config@example.com"

    import omym.config.settings as settings

    reloaded = importlib.reload(settings)

    assert reloaded.USE_MB_ROMANIZATION is False
    assert reloaded.MB_APP_NAME == "custom-app"
    assert reloaded.MB_APP_VERSION == "9.9.9"
    assert reloaded.MB_CONTACT == "mailto:config@example.com"
