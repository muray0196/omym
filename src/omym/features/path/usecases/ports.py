"""Ports for path use cases.

Where: features/path/usecases.
What: Protocols and records describing infrastructure interactions required by path logic.
Why: Allow adapters to satisfy filesystem/database/language dependencies without coupling use cases to concrete implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class FilterHierarchyRecord:
    """Hierarchy metadata required for assembling folder structures."""

    id: int
    name: str
    priority: int


@dataclass(slots=True)
class FilterValueRecord:
    """Filter value for a specific hierarchy/file combination."""

    hierarchy_id: int
    file_hash: str
    value: str


@runtime_checkable
class FilterQueryPort(Protocol):
    """Read access to filter hierarchies and values."""

    def get_hierarchies(self) -> list[FilterHierarchyRecord]:
        """Return hierarchies ordered by priority."""
        ...

    def get_values(self, hierarchy_id: int) -> list[FilterValueRecord]:
        """Return values for the given hierarchy identifier."""
        ...


@runtime_checkable
class ArtistCacheWriter(Protocol):
    """Port for persisting and retrieving artist identifiers."""

    def get_artist_id(self, artist_name: str) -> str | None:
        """Return a cached artist ID if present."""
        ...

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        """Persist a generated artist ID; returns True on success."""
        ...
