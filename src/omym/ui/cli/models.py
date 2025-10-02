"""src/omym/ui/cli/models.py
What: Shared UI-facing data structures for CLI presentation layers.
Why: Provide lightweight value objects without introducing import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class UnprocessedSummary:
    """Aggregate data that summarises unprocessed files for display."""

    total: int
    preview: list[str]
    truncated: bool


__all__ = ["UnprocessedSummary"]
