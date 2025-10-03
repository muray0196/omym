"""
/*
Path: src/omym/features/metadata/usecases/assets/__init__.py
Summary: Asset helper package marker and exports.
Why: Group artwork and lyric asset utilities for clarity.
*/
"""

"""Asset discovery and logging helpers for metadata processing."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import asset_detection, asset_logging, artwork_assets, associated_assets, lyrics_assets

__all__ = [
    "asset_detection",
    "asset_logging",
    "artwork_assets",
    "associated_assets",
    "lyrics_assets",
]


def __getattr__(name: str) -> Any:
    """Lazily import asset helper modules to avoid circular imports."""

    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
