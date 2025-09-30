"""Where: src/omym/features/metadata/usecases/track_metadata_extractor.py
What: Compatibility shim re-exporting metadata extraction entry point.
Why: Preserve historic import paths used throughout tests and older callers.
"""

from __future__ import annotations

from .extraction.track_metadata_extractor import MetadataExtractor

__all__ = ["MetadataExtractor"]
