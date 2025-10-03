"""
/*
Path: src/omym/features/metadata/usecases/cleanup/__init__.py
Summary: Cleanup helper package marker and exports.
Why: Isolate lifecycle management utilities for metadata processing.
*/
"""

"""Cleanup helpers for metadata processing workflows."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import unprocessed_cleanup

__all__ = ["unprocessed_cleanup"]


def __getattr__(name: str) -> Any:
    """Lazily import cleanup helpers to avoid circular imports."""

    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
