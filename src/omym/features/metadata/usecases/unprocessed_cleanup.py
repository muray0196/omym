"""src/omym/features/metadata/usecases/unprocessed_cleanup.py
What: Utilities to relocate unprocessed files into a dedicated review folder.
Why: Keep directory processors focused while centralising fallback clean-up logic.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from omym.platform.filesystem import ensure_parent_directory, remove_empty_directories
from omym.platform.logging import logger

from .processing_types import ProcessResult


def snapshot_unprocessed_candidates(
    root: Path,
    *,
    unprocessed_dir_name: str,
) -> set[Path]:
    """Capture file paths that should be evaluated after processing.

    The snapshot ignores files that already live inside the configured
    unprocessed area so repeat runs avoid redundant moves.
    """

    if not root.exists():
        return set()

    unprocessed_root = root / unprocessed_dir_name

    candidates: set[Path] = set()
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        if _is_within(entry, unprocessed_root):
            continue
        candidates.add(entry)

    return candidates


def relocate_unprocessed_files(
    root: Path,
    candidates: Iterable[Path],
    *,
    unprocessed_dir_name: str,
    dry_run: bool,
) -> list[tuple[Path, Path]]:
    """Relocate surviving snapshot files under the unprocessed folder.

    Returns a list of (source, destination) tuples for completed moves.
    """

    snapshot = list(candidates)
    if not snapshot:
        return []

    unprocessed_root = root / unprocessed_dir_name
    moves: list[tuple[Path, Path]] = []

    for original_path in sorted(snapshot):
        if not original_path.exists():
            continue
        try:
            relative_path = original_path.relative_to(root)
        except ValueError:
            continue

        destination = unprocessed_root / relative_path

        if dry_run:
            logger.info(
                "Dry run: unprocessed file would move", extra={
                    "source_path": str(original_path),
                    "planned_destination": str(destination),
                }
            )
            continue

        _ = ensure_parent_directory(destination)
        target_path = _next_available_destination(destination)
        _ = original_path.replace(target_path)
        moves.append((original_path, target_path))
        logger.info(
            "Moved unprocessed file", extra={
                "source_path": str(original_path),
                "target_path": str(target_path),
            }
        )

    if moves:
        remove_empty_directories(root)

    return moves


def calculate_pending_unprocessed(
    snapshot: Iterable[Path],
    results: Sequence[ProcessResult],
) -> set[Path]:
    """Determine which snapshot entries remain unprocessed after a run."""

    pending: set[Path] = {Path(candidate) for candidate in snapshot}

    for result in results:
        if not result.success:
            continue

        pending.discard(result.source_path)

        lyrics_result = result.lyrics_result
        if (
            lyrics_result is not None
            and lyrics_result.reason is None
        ):
            pending.discard(lyrics_result.source_path)

        for artwork_result in result.artwork_results:
            if artwork_result.reason is None:
                pending.discard(artwork_result.source_path)

    return {path for path in pending if path.exists()}


def _is_within(path: Path, ancestor: Path) -> bool:
    try:
        _ = path.relative_to(ancestor)
    except ValueError:
        return False
    return True


def _next_available_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent

    index = 1
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


__all__ = [
    "snapshot_unprocessed_candidates",
    "relocate_unprocessed_files",
    "calculate_pending_unprocessed",
]
