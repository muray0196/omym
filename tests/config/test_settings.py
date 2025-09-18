"""Tests for settings module behavior."""

from __future__ import annotations

import importlib


def test_use_mb_romanization_defaults_true(config_runtime_env: None) -> None:
    """Default configuration enables MusicBrainz romanization."""
    _ = config_runtime_env

    import omym.config.settings as settings

    reloaded = importlib.reload(settings)

    assert reloaded.USE_MB_ROMANIZATION is True


def test_musicbrainz_identity_uses_config_defaults(
    config_runtime_env: None,
) -> None:
    """MusicBrainz identity derives from config values."""

    _ = config_runtime_env

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
