"""Filesystem-related utilities shared across the domain layer."""

from __future__ import annotations

import os
from pathlib import Path


def remove_empty_directories(directory: Path) -> None:
    """Recursively remove empty directories starting from the given root.

    Args:
        directory: Root directory to inspect.
    """
    if not directory.exists():
        return

    for root, _, _ in os.walk(str(directory), topdown=False):
        root_path = Path(root)
        try:
            if root_path.exists() and not any(root_path.iterdir()):
                root_path.rmdir()
        except OSError:
            continue
