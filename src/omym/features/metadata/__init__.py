"""Public API for the metadata feature."""

from .domain.track_metadata import TrackMetadata
from .usecases.extraction import ArtistRomanizer, MetadataExtractor
from .usecases.music_file_processor import MusicProcessor
from .usecases.processing_types import (
    ArtworkProcessingResult,
    DirectoryRollbackError,
    LyricsProcessingResult,
    ProcessResult,
    ProcessingEvent,
    ProcessingLogContext,
)
from .usecases.ports import (
    ArtistCachePort,
    DatabaseManagerPort,
    ProcessingAfterPort,
    ProcessingBeforePort,
)

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
    "DatabaseManagerPort",
    "ProcessingBeforePort",
    "ProcessingAfterPort",
    "ArtistCachePort",
]
