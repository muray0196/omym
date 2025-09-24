"""Filesystem adapter for restoration use cases."""

from __future__ import annotations

import shutil
from pathlib import Path

from omym.platform.filesystem import ensure_parent_directory, remove_empty_directories

from ...usecases.ports import FileSystemGateway


class LocalFileSystemGateway(FileSystemGateway):
    """Thin wrapper around the local filesystem."""

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def ensure_parent(self, path: Path) -> Path:
        return ensure_parent_directory(path)

    def move(self, source: Path, destination: Path) -> None:
        _ = shutil.move(str(source), str(destination))

    def list_directory(self, path: Path) -> list[Path]:
        try:
            return [entry for entry in path.iterdir()]
        except OSError:
            return []

    def same_file(self, first: Path, second: Path) -> bool:
        try:
            return first.resolve() == second.resolve()
        except OSError:
            return False

    def remove_empty_directories(self, root: Path) -> None:
        remove_empty_directories(root)


__all__ = ["LocalFileSystemGateway"]
