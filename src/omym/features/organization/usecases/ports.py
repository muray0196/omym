"""Ports for organization use cases.

Where: features/organization/usecases.
What: Protocols describing database interactions needed by album/filter management.
Why: Decouple use cases from concrete SQLite DAO implementations while keeping tests injectable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class FilterHierarchyRecord:
    """Hierarchy metadata exposed to the filtering use case."""

    id: int
    name: str
    priority: int


@runtime_checkable
class FilterRegistryPort(Protocol):
    """Port for managing hierarchical filter definitions and values."""

    def insert_hierarchy(self, name: str, priority: int) -> int | None:
        """Persist a new hierarchy level; return its identifier when successful."""
        ...

    def get_hierarchies(self) -> list[FilterHierarchyRecord]:
        """Return configured hierarchies ordered by priority."""
        ...

    def insert_value(self, hierarchy_id: int, file_hash: str, value: str) -> bool:
        """Store a value for ``file_hash`` at the given hierarchy."""
        ...


@dataclass(slots=True)
class AlbumRecord:
    """Album metadata snapshot consumed by album management."""

    id: int
    album_name: str
    album_artist: str
    year: int | None
    total_tracks: int | None
    total_discs: int | None


@runtime_checkable
class AlbumRepositoryPort(Protocol):
    """Port for reading/writing album state and track positions."""

    def get_album(self, album_name: str, album_artist: str) -> AlbumRecord | None:
        """Look up an album by name/artist."""

    def insert_album(
        self,
        album_name: str,
        album_artist: str,
        year: int | None = None,
        total_tracks: int | None = None,
        total_discs: int | None = None,
    ) -> int | None:
        """Persist a new album and return its identifier when successful."""
        ...

    def insert_track_position(
        self,
        album_id: int,
        disc_number: int,
        track_number: int,
        file_hash: str,
    ) -> bool:
        """Record the mapping from album/disc/track to ``file_hash``."""
        ...

    def check_track_continuity(self, album_id: int) -> tuple[bool, list[str]]:
        """Verify disc/track ordering and return ``(is_continuous, warnings)``."""
        ...
