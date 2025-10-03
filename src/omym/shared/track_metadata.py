# Where: omym.shared.track_metadata
# What: Canonical TrackMetadata dataclass shared across features.
# Why: Centralize metadata representation for reuse and consistency.

from dataclasses import dataclass


@dataclass
class TrackMetadata:
    """Metadata for a music track."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    genre: str | None = None
    year: int | None = None
    track_number: int | None = None
    track_total: int | None = None
    disc_number: int | None = None
    disc_total: int | None = None
    file_extension: str | None = None


__all__ = ["TrackMetadata"]
