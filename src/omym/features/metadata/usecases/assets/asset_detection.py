"""src/omym/features/metadata/usecases/assets/asset_detection.py
What: Detect nearby lyrics or artwork assets for a track file.
Why: Share discovery logic between file processing flows.
"""

from __future__ import annotations

from pathlib import Path


def find_associated_lyrics(file_path: Path) -> tuple[Path | None, list[str]]:
    """Locate an .lrc file that shares the same stem as the given music file."""

    parent = file_path.parent
    warnings: list[str] = []

    if not parent.exists():
        return None, warnings

    try:
        candidates = [
            candidate
            for candidate in parent.iterdir()
            if candidate.is_file()
            and candidate.stem == file_path.stem
            and candidate.suffix.lower() == ".lrc"
        ]
    except OSError:
        return None, warnings

    if not candidates:
        return None, warnings

    candidates.sort()
    if len(candidates) > 1:
        warnings.append(
            f"Multiple lyrics files found for {file_path.name}; using {candidates[0].name}"
        )

    return candidates[0], warnings


def resolve_directory_artwork(
    file_path: Path,
    *,
    supported_track_extensions: set[str],
    supported_image_extensions: set[str],
) -> tuple[list[Path], bool]:
    """Resolve artwork files in the same directory if the track is primary."""

    parent = file_path.parent
    if not parent.exists():
        return [], False

    try:
        entries = [candidate for candidate in parent.iterdir() if candidate.is_file()]
    except OSError:
        return [], False

    supported_tracks = sorted(
        entry for entry in entries if entry.suffix.lower() in supported_track_extensions
    )
    if not supported_tracks or supported_tracks[0] != file_path:
        return [], False

    artworks = sorted(
        entry for entry in entries if entry.suffix.lower() in supported_image_extensions
    )
    return artworks, True


__all__ = ["find_associated_lyrics", "resolve_directory_artwork"]
