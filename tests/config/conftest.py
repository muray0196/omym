"""Shared pytest fixtures for configuration-focused tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def portable_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Provide a temporary repository root for portable path detection."""

    _ = (tmp_path / "pyproject.toml").write_text("[project]\nname='tmp'\n")

    import omym.config.paths as paths

    def _fake_detect_repo_root(_start: Path | None = None) -> Path:
        return tmp_path

    monkeypatch.setattr(paths, "_detect_repo_root", _fake_detect_repo_root, raising=True)
    return tmp_path


@pytest.fixture
def config_runtime_env(
    _portable_repo_root: Path
) -> Iterator[None]:
    """Reset configuration singletons around a test run."""

    import omym.config.config as config_module

    original_instance = config_module.Config._instance  # pyright: ignore[reportPrivateUsage]
    original_loaded_from = config_module.Config._loaded_from  # pyright: ignore[reportPrivateUsage]
    original_config = config_module.config

    config_module.Config._instance = None  # pyright: ignore[reportPrivateUsage]
    config_module.Config._loaded_from = None  # pyright: ignore[reportPrivateUsage]
    config_module.config = config_module.Config.load()

    try:
        yield None
    finally:
        config_module.Config._instance = original_instance  # pyright: ignore[reportPrivateUsage]
        config_module.Config._loaded_from = original_loaded_from  # pyright: ignore[reportPrivateUsage]
        config_module.config = original_config

