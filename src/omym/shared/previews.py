"""Shared preview cache value objects (domain <-> adapters).

Where: shared/.
What: Dataclasses describing cached dry-run previews reused across layers.
Why: Centralize the preview cache contract so ports and adapters stay in sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["PreviewCacheEntry"]


@dataclass(frozen=True, slots=True)
class PreviewCacheEntry:
    """Value object describing a cached dry-run preview."""

    file_hash: str
    source_path: Path
    base_path: Path
    target_path: Path | None
    payload: dict[str, object]

