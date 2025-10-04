"""Summary: Ports defining metadata use case dependencies.
Why: Decouple use cases from concrete adapters so tests and swaps stay simple."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection
from typing import Protocol, runtime_checkable

from omym.shared import PreviewCacheEntry
from omym.shared.track_metadata import TrackMetadata


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


@runtime_checkable
class RomanizationPort(Protocol):
    """Port abstracting MusicBrainz romanization helpers."""

    def configure_cache(self, cache: ArtistCachePort | None) -> None:
        """Attach the persistence layer used by remote fetch helpers."""
        ...

    def fetch_romanized_name(self, artist_name: str) -> str | None:
        """Retrieve a romanized name for ``artist_name`` when available."""
        ...

    def save_cached_name(
        self,
        original: str,
        romanized: str,
        *,
        source: str | None = None,
    ) -> None:
        """Persist a romanized mapping so future runs reuse the value."""
        ...


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


@runtime_checkable
class FilesystemPort(Protocol):
    """Port abstracting filesystem directory management helpers."""

    def ensure_parent_directory(self, path: Path) -> Path:
        """Ensure the parent directory for ``path`` exists and return it."""
        ...

    def remove_empty_directories(self, directory: Path) -> None:
        """Recursively remove empty directories rooted at ``directory``."""
        ...


@runtime_checkable
class ArtistIdGeneratorPort(Protocol):
    """Port for generating stable artist identifiers from metadata."""

    def generate(self, artist_name: str | None) -> str:
        """Return a deterministic identifier for ``artist_name``."""
        ...


@runtime_checkable
class DirectoryNamingPort(Protocol):
    """Port exposing album-directory generation helpers."""

    def register_album_year(self, metadata: TrackMetadata) -> None:
        """Record album-year metadata so subsequent calls stay consistent."""
        ...

    def generate(self, metadata: TrackMetadata) -> Path:
        """Build the relative directory path for ``metadata``."""
        ...


@runtime_checkable
class FileNameGenerationPort(Protocol):
    """Port exposing sanitized track file-name generation helpers."""

    def register_album_track_width(self, metadata: TrackMetadata) -> None:
        """Update cached width calculations for ``metadata``'s album."""
        ...

    def generate(self, metadata: TrackMetadata) -> str:
        """Build the sanitized file name for ``metadata``."""
        ...


@dataclass(slots=True)
class RenamerPorts:
    """Bundle the renamer-related ports used by metadata processing flows."""

    directory: DirectoryNamingPort
    file_name: FileNameGenerationPort
    artist_id: ArtistIdGeneratorPort


__all__ = [
    "DatabaseManagerPort",
    "ProcessingBeforePort",
    "ProcessingAfterPort",
    "ArtistCachePort",
    "RomanizationPort",
    "PreviewCachePort",
    "FilesystemPort",
    "ArtistIdGeneratorPort",
    "DirectoryNamingPort",
    "FileNameGenerationPort",
    "RenamerPorts",
]
