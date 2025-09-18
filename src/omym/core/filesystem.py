"""Filesystem helpers reused across multiple layers."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_directory(directory: Path) -> Path:
    """Ensure ``directory`` exists as a folder and return it."""

    if directory.exists():
        if not directory.is_dir():
            raise NotADirectoryError(f"Path exists but is not a directory: {directory}")
        return directory

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_parent_directory(path: Path) -> Path:
    """Ensure the parent directory for ``path`` exists and return it."""

    parent = path.parent
    return ensure_directory(parent)


def remove_empty_directories(directory: Path) -> None:
    """Recursively remove empty directories starting from the given root."""

    if not directory.exists():
        return

    for root, _, _ in os.walk(str(directory), topdown=False):
        root_path = Path(root)
        try:
            if root_path.exists() and not any(root_path.iterdir()):
                root_path.rmdir()
        except OSError:
            continue


__all__ = ["ensure_directory", "ensure_parent_directory", "remove_empty_directories"]
