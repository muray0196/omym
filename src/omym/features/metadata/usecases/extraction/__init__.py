"""Metadata extraction subpackage.

Where: src/omym/features/metadata/usecases/extraction/__init__.py
What: Expose public entry points for metadata extraction components.
Why: Provide a single import surface after reorganizing extraction modules.
"""

from .artist_cache_adapter import DryRunArtistCacheAdapter
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
    "DryRunArtistCacheAdapter",
    "Mp3Extractor",
    "FlacExtractor",
    "OpusExtractor",
    "M4aExtractor",
    "DsfExtractor",
]
