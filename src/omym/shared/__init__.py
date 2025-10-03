# Where: omym.shared.__init__
# What: Provide a concise import surface for shared utilities and dataclasses.
# Why: Encourage consistent reuse of shared helpers across features.

"""Shared cross-cutting utilities exposed at the package level."""

from .path_components import ComponentValue
from .previews import PreviewCacheEntry
from .track_metadata import TrackMetadata

__all__ = ["ComponentValue", "PreviewCacheEntry", "TrackMetadata"]
