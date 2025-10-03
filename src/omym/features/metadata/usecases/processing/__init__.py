"""
/*
Path: src/omym/features/metadata/usecases/processing/__init__.py
Summary: Processing orchestration package marker and exports.
Why: Provide a clear namespace for music metadata processing workflows.
*/
"""

"""Processing orchestration helpers for metadata use cases."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import directory_runner, file_runner, music_file_processor, processing_types

__all__ = [
    "directory_runner",
    "file_runner",
    "music_file_processor",
    "processing_types",
]


def __getattr__(name: str) -> Any:
    """Lazily import processing modules to avoid circular imports."""

    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
