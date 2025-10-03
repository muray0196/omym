"""src/omym/features/metadata/usecases/assets/associated_assets.py
What: Convenience re-export for asset detection and handling helpers.
Why: Preserve existing import surface while splitting hefty modules.
"""

from __future__ import annotations

from .asset_detection import find_associated_lyrics, resolve_directory_artwork
from .asset_logging import ProcessLogger
from .artwork_assets import process_artwork, summarize_artwork
from .lyrics_assets import process_lyrics, summarize_lyrics

__all__ = [
    "ProcessLogger",
    "find_associated_lyrics",
    "resolve_directory_artwork",
    "process_lyrics",
    "process_artwork",
    "summarize_lyrics",
    "summarize_artwork",
]
