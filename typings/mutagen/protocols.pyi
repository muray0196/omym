from typing import TypeVar, TypeAlias, Protocol

__all__ = ["MutagenTags", "MutagenTagsBytes", "TagValue", "TagsDict"]

# Generic type
T = TypeVar(name="T")

# Type definitions for tag values
TagValue: TypeAlias = str | list[str] | list[tuple[int, int]] | None
TagsDict: TypeAlias = dict[str, TagValue]

class MutagenTags(Protocol):
    """Protocol for mutagen tags."""

    def get(self, key: str, default: T | None = None) -> TagValue | T: ...
    def items(self) -> list[tuple[str, TagValue]]: ...

class MutagenTagsBytes(Protocol):
    """Protocol for mutagen tags that use bytes."""

    def get(self, key: bytes, default: T | None = None) -> bytes | T: ...
    def items(self) -> list[tuple[bytes, bytes]]: ...
