"""Shared path utilities for configuration and data locations.

This module centralizes how the application discovers locations for
config and data files.

Policy (portable by default):
- Config: repository-root ``<repo_root>/config/config.toml``
- Artist name preferences: repository-root ``<repo_root>/config/artist_name_preferences.toml``
- Data: repository-root ``<repo_root>/.data`` unless overridden by
  ``OMYM_DATA_DIR``.
"""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Mapping
from typing import Callable, Final


_ENV_DATA_DIR: Final[str] = "OMYM_DATA_DIR"


def resolve_overridable_path(
    *,
    explicit_path: Path | str | None,
    env: Mapping[str, str] | None,
    env_var: str | None,
    default_factory: Callable[[], Path],
) -> Path:
    """Resolve a configuration path honoring explicit and environment overrides."""

    if explicit_path is not None:
        return Path(explicit_path).expanduser().resolve()

    mapping = env if env is not None else os.environ
    if env_var:
        candidate = mapping.get(env_var) or ""
        candidate = candidate.strip()
        if candidate:
            return Path(candidate).expanduser().resolve()

    default_path = default_factory()
    return default_path.expanduser().resolve()


def _detect_repo_root(start: Path | None = None) -> Path:
    """Detect the repository root by walking up parents.

    Looks for markers like ``pyproject.toml`` or ``.git``.

    Args:
        start: Starting path. Defaults to this file's directory.

    Returns:
        Path: Detected repository root, or the provided start's root parent
        if no marker is found.
    """
    here = (start or Path(__file__).resolve()).parent
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
    # Fallback: use current working directory if detection fails
    return Path.cwd()


def default_config_path() -> Path:
    """Get the default path to the main TOML config file.

    Portable layout: ``<repo_root>/config/config.toml``.
    """
    repo_root = _detect_repo_root()
    return (repo_root / "config" / "config.toml").resolve()


def default_artist_name_preferences_path() -> Path:
    """Get the default path to the artist name preferences file.

    Portable layout: ``<repo_root>/config/artist_name_preferences.toml``.
    """
    repo_root = _detect_repo_root()
    return (repo_root / "config" / "artist_name_preferences.toml").resolve()


def default_data_dir() -> Path:
    """Get the default directory for app data (e.g., the SQLite DB)."""

    return resolve_overridable_path(
        explicit_path=None,
        env=None,
        env_var=_ENV_DATA_DIR,
        default_factory=lambda: (_detect_repo_root() / ".data").resolve(),
    )


def default_log_dir() -> Path:
    """Get the default directory for log files."""

    return (_detect_repo_root() / "logs").resolve()


def default_log_file() -> Path:
    """Get the default log file path."""

    return (default_log_dir() / "omym.log").resolve()


__all__ = [
    "default_config_path",
    "default_artist_name_preferences_path",
    "default_data_dir",
    "default_log_dir",
    "default_log_file",
    "resolve_overridable_path",
]
