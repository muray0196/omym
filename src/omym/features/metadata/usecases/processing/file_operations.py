"""Summary: Hashing and renaming helpers supporting metadata processing flows.
Why: Keep filesystem operations isolated from adapters while coordinating ports."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

from omym.config.settings import FILE_HASH_CHUNK_SIZE
from omym.platform.logging import logger

from ..assets import ProcessLogger
from ..ports import (
    DirectoryNamingPort,
    FileNameGenerationPort,
    FilesystemPort,
)
from .processing_types import ProcessingEvent
from omym.shared.track_metadata import TrackMetadata


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for byte_block in iter(lambda: handle.read(FILE_HASH_CHUNK_SIZE), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def find_available_path(target_path: Path, *, existing_path: Path | None = None) -> Path:
    """Find an available file path by appending a number if needed."""

    if not target_path.exists():
        return target_path

    if existing_path is not None:
        try:
            if target_path.samefile(existing_path):
                return target_path
        except FileNotFoundError:
            pass

    parent = target_path.parent
    stem = target_path.stem
    extension = target_path.suffix
    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){extension}"
        if not candidate.exists():
            return candidate
        counter += 1


def generate_target_path(
    base_path: Path,
    *,
    directory_generator: DirectoryNamingPort,
    file_name_generator: FileNameGenerationPort,
    metadata: TrackMetadata,
    existing_path: Path | None = None,
) -> Path | None:
    """Generate a target path for a file based on its metadata."""

    try:
        dir_path = directory_generator.generate(metadata)
        file_name = file_name_generator.generate(metadata)
        if not dir_path or not file_name:
            return None
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Error generating target path: %s", exc)
        return None

    target_path = base_path / dir_path / file_name
    return find_available_path(target_path, existing_path=existing_path)


def move_file(
    src_path: Path,
    dest_path: Path,
    *,
    log: ProcessLogger,
    filesystem: FilesystemPort,
    process_id: str | None = None,
    sequence: int | None = None,
    total: int | None = None,
    source_root: Path | None = None,
    target_root: Path | None = None,
) -> None:
    """Move a file from the source path to the target path."""

    _ = filesystem.ensure_parent_directory(dest_path)
    log(
        logging.INFO,
        ProcessingEvent.FILE_MOVE,
        "Moving file [id=%s, src=%s, dest=%s]",
        process_id or "-",
        src_path,
        dest_path,
        process_id=process_id,
        sequence=sequence,
        total_files=total,
        source_path=src_path,
        source_base_path=source_root or src_path.parent,
        target_path=dest_path,
        target_base_path=target_root or dest_path.parent,
    )
    _ = shutil.move(str(src_path), str(dest_path))


__all__ = [
    "calculate_file_hash",
    "find_available_path",
    "generate_target_path",
    "move_file",
]
