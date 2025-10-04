# Where: omym.features.metadata.__init__
# What: Expose metadata feature services and shared dataclasses.
# Why: Provide a cohesive import surface for UI and integration layers.

from omym.shared.track_metadata import TrackMetadata
from .usecases.extraction import ArtistRomanizer, MetadataExtractor
from .usecases.music_file_processor import MusicProcessor
from .usecases import assets, processing
from .usecases.processing import (
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
    FilesystemPort,
    ProcessingAfterPort,
    ProcessingBeforePort,
)

__all__ = [
    "TrackMetadata",
    "ArtistRomanizer",
    "MusicProcessor",
    "MetadataExtractor",
    "assets",
    "processing",
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
    "FilesystemPort",
]
