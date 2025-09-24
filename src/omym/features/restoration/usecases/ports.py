"""Ports for the restoration feature."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable
from typing import Protocol


@dataclass(slots=True, frozen=True)
class RestoreCandidate:
    """Data projected from persistence to construct a restore plan."""

    file_hash: str
    staged_path: Path
    original_path: Path


class RestorePlanReader(Protocol):
    """Fetch staged files eligible for restoration."""

    def fetch_restore_candidates(
        self,
        *,
        source_root: Path | None,
        limit: int | None = None,
    ) -> Iterable[RestoreCandidate]:
        """Yield candidates filtered by the staging root."""

        ...


class MaintenanceGateway(Protocol):
    """Perform destructive maintenance actions after successful runs."""

    def clear_all(self) -> bool:
        """Remove cached state; returns True on success."""

        ...


class FileSystemGateway(Protocol):
    """Abstract filesystem operations needed by the use cases."""

    def exists(self, path: Path) -> bool:
        """Return True if the path exists."""

        ...

    def is_file(self, path: Path) -> bool:
        """Return True when the path points to a regular file."""

        ...

    def ensure_parent(self, path: Path) -> Path:
        """Ensure the parent directory exists and return it."""

        ...

    def move(self, source: Path, destination: Path) -> None:
        """Move or rename the source to the destination."""

        ...

    def list_directory(self, path: Path) -> list[Path]:
        """Return the immediate entries within ``path``; missing directories yield an empty list."""

        ...

    def same_file(self, first: Path, second: Path) -> bool:
        """Return True when ``first`` and ``second`` address the same filesystem entry."""

        ...

    def remove_empty_directories(self, root: Path) -> None:
        """Recursively prune empty directories from ``root`` downward."""

        ...
