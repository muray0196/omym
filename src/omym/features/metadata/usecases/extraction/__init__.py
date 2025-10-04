"""
Summary: Public surface for metadata extraction modules.
Why: Provide a stable import path for orchestrators and tests.
"""

from .artist_romanizer import ArtistRomanizer
from .format_extractors import (
    DsfExtractor,
    FlacExtractor,
    M4aExtractor,
    Mp3Extractor,
    OpusExtractor,
)
from .track_metadata_extractor import MetadataExtractor

__all__ = [
    "MetadataExtractor",
    "ArtistRomanizer",
    "Mp3Extractor",
    "FlacExtractor",
    "OpusExtractor",
    "M4aExtractor",
    "DsfExtractor",
]
