"""Type definitions for mutagen types."""

from typing import Any, List, Optional, Protocol, Tuple, Union

class MutagenTags(Protocol):
    """Protocol for mutagen tags."""

    def get(
        self, key: str, default: Optional[Any] = None
    ) -> Optional[Union[str, List[str], List[Tuple[int, int]]]]: ...
    def items(self) -> List[Tuple[str, Any]]: ...

class MutagenFile(Protocol):
    """Protocol for mutagen file objects."""

    tags: Optional[MutagenTags]

    def get(
        self, key: str, default: Optional[Any] = None
    ) -> Optional[Union[str, List[str], List[Tuple[int, int]]]]: ...
