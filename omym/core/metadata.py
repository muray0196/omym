"""Metadata related functionality."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TrackMetadata:
    """Metadata for a music track."""

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    track_number: Optional[int] = None
    track_total: Optional[int] = None
    disc_number: Optional[int] = None
    disc_total: Optional[int] = None
    file_extension: Optional[str] = None
