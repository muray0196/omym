"""
/*
Path: src/omym/features/metadata/usecases/file_management/__init__.py
Summary: File management helper package marker and exports.
Why: Collect file handling utilities for reuse across processing flows.
*/
"""

"""Shared file management utilities for metadata use cases."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import file_context, file_duplicate, file_operations, file_success

__all__ = [
    "file_context",
    "file_duplicate",
    "file_operations",
    "file_success",
]


def __getattr__(name: str) -> Any:
    """Lazily import file management helpers to avoid circular imports."""

    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
