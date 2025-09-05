"""Shared path utilities for configuration and data locations.

This module centralizes how the application discovers locations for
config and data files.

Policy (portable by default):
- Config: repository-root ``<repo_root>/.config/omym/config.toml``
- Data: repository-root ``<repo_root>/.data`` unless overridden by
  ``OMYM_DATA_DIR``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final


_ENV_DATA_DIR: Final[str] = "OMYM_DATA_DIR"


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

    Portable layout: ``<repo_root>/.config/omym/config.toml``.
    """
    repo_root = _detect_repo_root()
    return (repo_root / ".config" / "omym" / "config.toml").resolve()


def default_data_dir() -> Path:
    """Get the default directory for app data (e.g., the SQLite DB).

    Honors the ``OMYM_DATA_DIR`` environment variable when set, else
    resolves to ``<repo_root>/.data``.
    """
    env_dir = os.getenv(_ENV_DATA_DIR)
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    repo_root = _detect_repo_root()
    return (repo_root / ".data").resolve()


__all__ = [
    "default_config_path",
    "default_data_dir",
]
