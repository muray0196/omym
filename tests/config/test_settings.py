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

    yield

    # Clean up singletons after test
    config_module.Config._instance = None  # pyright: ignore[reportPrivateUsage]
    config_module.Config._loaded_from = None  # pyright: ignore[reportPrivateUsage]


def test_use_mb_romanization_defaults_true(
    isolated_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default configuration enables MusicBrainz romanization."""
    _ = isolated_environment
    monkeypatch.delenv("OMYM_USE_MB_ROMANIZATION", raising=False)

    import omym.config.settings as settings

    reloaded = importlib.reload(settings)

    assert reloaded.USE_MB_ROMANIZATION is True


def test_use_mb_romanization_env_override(
    isolated_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Environment variable overrides configuration flag."""
    _ = isolated_environment
    monkeypatch.setenv("OMYM_USE_MB_ROMANIZATION", "0")

    import omym.config.settings as settings

    reloaded = importlib.reload(settings)

    assert reloaded.USE_MB_ROMANIZATION is False
