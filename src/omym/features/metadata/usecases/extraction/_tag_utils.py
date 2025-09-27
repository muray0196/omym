"""Tag utility helpers.

Where: src/omym/features/metadata/usecases/extraction/_tag_utils.py
What: Provide pure helper routines for parsing and safe metadata tag access.
Why: Support refactoring of the track metadata extractor into smaller units while preserving behaviour.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mutagen import MutagenTagsBytes, TagValue, TagsDict
else:  # pragma: no cover - typing convenience
    MutagenTagsBytes: type[object] = object
    TagValue: type[object] = object
    TagsDict: type[dict[str, Any]] = dict

__all__ = [
    "convert_bytes_tags",
    "safe_get_first",
    "safe_get_dsf",
    "parse_slash_separated",
    "parse_tuple_numbers",
    "parse_year",
]


def convert_bytes_tags(tags: MutagenTagsBytes) -> TagsDict:
    """Convert byte tags to string tags.

    Args:
        tags: Tags with byte keys and values.

    Returns:
        Dictionary with string keys and values.
    """
    result: TagsDict = {}
    for key, value in tags.items():
        try:
            str_key: str = key.decode(encoding="utf-8")
            str_value: str = value.decode(encoding="utf-8")
            result[str_key] = str_value
        except (UnicodeDecodeError, AttributeError):
            continue
    return result


def safe_get_first(data: list[str] | None, default: str = "") -> str:
    """Safely get the first element from a list or return the default."""
    return data[0] if data else default


def safe_get_dsf(tags: TagsDict, key: str, default: str = "") -> str:
    """Safely get a DSF tag value from a dictionary."""
    try:
        value: TagValue = tags.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def parse_slash_separated(value: str) -> tuple[int | None, int | None]:
    """Parse a string in 'number/total' format.

    Returns a tuple (number, total) or (None, None) if conversion fails.
    """
    parts: list[str] = value.split(sep="/") if value else []
    num: int | None = int(parts[0]) if parts and parts[0].isdigit() else None
    total: int | None = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    return num, total


def parse_tuple_numbers(data: list[tuple[int, int]] | None) -> tuple[int | None, int | None]:
    """Parse a list of numeric tuples and return the first tuple with zeros converted to None."""
    if data:
        first: tuple[int, int] = data[0]
        num: int | None = first[0] if first[0] != 0 else None
        total: int | None = first[1] if first[1] != 0 else None
        return num, total
    return None, None


def parse_year(date_str: str) -> int | None:
    """Parse a year from a string (expects the first 4 characters to be digits)."""
    return int(date_str[:4]) if date_str and len(date_str) >= 4 and date_str[:4].isdigit() else None
