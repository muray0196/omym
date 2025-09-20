"""Utilities for parsing organization path formats."""

from __future__ import annotations


def parse_path_format(path_format: str, separator: str = "/") -> list[str]:
    """Normalize a path format definition into ordered components.

    Args:
        path_format: Raw format string such as "AlbumArtist/Album/Year".
        separator: Character used to delineate components in ``path_format``.

    Returns:
        list[str]: Ordered, trimmed path components with empty segments removed.

    Raises:
        ValueError: If ``separator`` is an empty string.
    """
    if not separator:
        raise ValueError("Path format separator must not be empty.")

    normalized_components: list[str] = []
    for raw_component in path_format.split(separator):
        component = raw_component.strip()
        if component:
            normalized_components.append(component)

    return normalized_components
