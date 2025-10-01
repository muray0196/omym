"""Ports defining metadata use case dependencies.

Where: features/metadata/usecases.
What: Protocols capturing the interactions MusicProcessor needs.
Why: Decouple use cases from concrete DB and cache adapters for testing and swaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection
from typing import Protocol, runtime_checkable


@runtime_checkable
class DatabaseManagerPort(Protocol):
    """Port for database lifecycle management."""

    conn: Connection | None

    def connect(self) -> None:
        """Ensure the underlying connection is ready."""
        ...

    def close(self) -> None:
        """Tear down the managed connection."""
        ...


@runtime_checkable
class ProcessingBeforePort(Protocol):
    """Port for persisting source file state before processing."""

    def check_file_exists(self, file_hash: str) -> bool:
        """Return True if the file already has processing state."""
        ...

    def get_target_path(self, file_hash: str) -> Path | None:
        """Resolve the previously recorded target path, if any."""
        ...

    def insert_file(self, file_hash: str, file_path: Path) -> bool:
        """Persist or update the source file location."""
        ...


@runtime_checkable
class ProcessingAfterPort(Protocol):
    """Port for persisting post-processing file state."""

    def insert_file(self, file_hash: str, file_path: Path, target_path: Path) -> bool:
        """Persist or update the processed file location."""
        ...


@runtime_checkable
class ArtistCachePort(Protocol):
    """Port for artist identifier and romanization caching."""

    def insert_artist_id(self, artist_name: str, artist_id: str) -> bool:
        """Upsert a generated artist identifier."""
        ...

    def get_artist_id(self, artist_name: str) -> str | None:
        """Look up a cached artist identifier."""
        ...

    def get_romanized_name(self, artist_name: str) -> str | None:
        """Look up a cached romanized artist name."""
        ...

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        """Store a romanized artist name with provenance."""
        ...

    def clear_cache(self) -> bool:
        """Erase cached artist data."""
        ...


@dataclass(frozen=True, slots=True)
class PreviewCacheEntry:
    """Value object describing a cached dry-run preview."""

    file_hash: str
    source_path: Path
    base_path: Path
    target_path: Path | None
    payload: dict[str, object]


@runtime_checkable
class PreviewCachePort(Protocol):
    """Port for cached dry-run preview access."""

    def upsert_preview(
        self,
        *,
        file_hash: str,
        source_path: Path,
        base_path: Path,
        target_path: Path | None,
        payload: dict[str, object],
    ) -> bool:
        """Insert or update a preview entry."""
        ...

    def get_preview(self, file_hash: str) -> PreviewCacheEntry | None:
        """Fetch a preview entry if available."""
        ...

    def delete_preview(self, file_hash: str) -> bool:
        """Remove a cached preview entry."""
        ...
