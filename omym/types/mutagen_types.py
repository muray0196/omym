"""Type definitions for mutagen types."""

from typing import Any, Protocol


class MutagenTags(Protocol):
    """Protocol for mutagen tags."""

    def get(self, key: str, default: Any | None = None) -> str | list[str] | list[tuple[int, int]] | None: ...
    def items(self) -> list[tuple[str, Any]]: ...


class MutagenFile(Protocol):
    """Protocol for mutagen file objects."""

    tags: MutagenTags | None

    def get(self, key: str, default: Any | None = None) -> str | list[str] | list[tuple[int, int]] | None: ...
