"""src/omym/features/metadata/adapters/filesystem_adapter.py
What: Adapter implementing FilesystemPort on top of platform helpers.
Why: Keep filesystem I/O in adapters while use cases target abstractions."""

from __future__ import annotations

from pathlib import Path

from omym.features.metadata.usecases.ports import FilesystemPort
from omym.platform.filesystem import ensure_parent_directory, remove_empty_directories


class LocalFilesystemAdapter(FilesystemPort):
    """Adapter delegating filesystem helpers to the shared platform module."""

    def ensure_parent_directory(self, path: Path) -> Path:
        return ensure_parent_directory(path)

    def remove_empty_directories(self, directory: Path) -> None:
        remove_empty_directories(directory)


__all__ = ["LocalFilesystemAdapter"]
