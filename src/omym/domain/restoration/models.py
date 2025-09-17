"""Data structures that describe music library restoration plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Final


class CollisionPolicy(str, Enum):
    """Represent how to handle collisions when restoring files."""

    ABORT = "abort"
    SKIP = "skip"
    BACKUP = "backup"

    @staticmethod
    def from_user_input(value: str) -> "CollisionPolicy":
        """Translate raw CLI input into the matching policy."""

        normalized = value.strip().lower()
        for policy in CollisionPolicy:
            if policy.value == normalized:
                return policy
        valid: Final[str] = ", ".join(p.value for p in CollisionPolicy)
        msg = f"Unsupported collision policy '{value}'. Valid options: {valid}"
        raise ValueError(msg)


@dataclass(slots=True, frozen=True)
class RestorePlanItem:
    """Describe a single planned restore operation."""

    file_hash: str
    source_path: Path
    destination_path: Path


@dataclass(slots=True)
class RestoreResult:
    """Capture the outcome of executing a plan item."""

    plan: RestorePlanItem
    moved: bool
    message: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RestoreRequest:
    """Inputs required to build and execute a restoration run."""

    source_root: Path
    destination_root: Path | None
    dry_run: bool
    collision_policy: CollisionPolicy
    backup_suffix: str
    continue_on_error: bool
    limit: int | None = None
