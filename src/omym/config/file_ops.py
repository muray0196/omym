"""Utility helpers for configuration file persistence."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def ensure_file_with_template(path: Path, *, template_provider: Callable[[], object]) -> bool:
    """Create ``path`` using the supplied template when it does not exist.

    Args:
        path: Target file to create.
        template_provider: Callable returning the file contents to write.

    Returns:
        bool: ``True`` when the file was created, ``False`` if it already existed.
    """

    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    content = template_provider()
    if not isinstance(content, str):  # Defensive programming against template bugs.
        raise TypeError("Template provider must return a string")

    _ = path.write_text(content, encoding="utf-8")
    return True


def write_text_file(path: Path, content: str) -> None:
    """Persist textual content ensuring parent directories exist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


__all__ = ["ensure_file_with_template", "write_text_file"]
