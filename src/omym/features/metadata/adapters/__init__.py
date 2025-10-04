"""
Summary: Package marker for metadata adapters.
Why: Keep adapter exports together for easy discovery.
"""

from .artist_cache_adapter import DryRunArtistCacheAdapter
from .filesystem_adapter import LocalFilesystemAdapter
from .romanization_adapter import MusicBrainzRomanizationAdapter

__all__ = [
    "DryRunArtistCacheAdapter",
    "LocalFilesystemAdapter",
    "MusicBrainzRomanizationAdapter",
]
