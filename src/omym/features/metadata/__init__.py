"""Public API for the metadata feature."""

from .domain.track_metadata import TrackMetadata
from .usecases.artist_romanizer import ArtistRomanizer
from .usecases.music_file_processor import (
    ArtworkProcessingResult,
    DirectoryRollbackError,
    LyricsProcessingResult,
    ProcessResult,
    ProcessingEvent,
    ProcessingLogContext,
    MusicProcessor,
)
from .usecases.track_metadata_extractor import MetadataExtractor

__all__ = [
    "TrackMetadata",
    "ArtistRomanizer",
    "MusicProcessor",
    "MetadataExtractor",
    "ProcessingEvent",
    "ProcessResult",
    "DirectoryRollbackError",
    "ProcessingLogContext",
    "LyricsProcessingResult",
    "ArtworkProcessingResult",
]
