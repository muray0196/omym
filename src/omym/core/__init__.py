"""Core utilities shared across OMYM layers."""

from .filesystem import ensure_directory, ensure_parent_directory, remove_empty_directories

__all__ = [
    "ensure_directory",
    "ensure_parent_directory",
    "remove_empty_directories",
]
