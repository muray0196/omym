# Path: `tests/features/metadata/usecases/test_file_operations.py`
# Summary: Validate hashing and target path generation behaviours in metadata use cases.
# Why: Confirm sanitization failures propagate as logged errors instead of silent domain logs.

"""Where: tests/features/metadata/usecases/test_file_operations.py
What: Regression tests for file hashing behaviour in metadata use cases.
Why: Ensure hashing results stay stable when chunk sizing is configurable.
Assumptions: - hashlib.sha256 remains deterministic for identical inputs.
Trade-offs: - Uses monkeypatch to override module constant instead of config reload.
"""

from __future__ import annotations

import hashlib

from pathlib import Path
from typing import cast

import pytest

from omym.features.metadata.usecases.processing import file_operations
from omym.features.path import DirectoryGenerator, FileNameGenerator, SanitizerError
from omym.shared.track_metadata import TrackMetadata


def test_calculate_file_hash_matches_sha256(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Validate configured chunked hashing matches hashlib.sha256 output."""

    sample_path = tmp_path / "example.bin"
    content = (b"abc123" * 1024) + b"omym"
    _ = sample_path.write_bytes(content)

    monkeypatch.setattr(file_operations, "FILE_HASH_CHUNK_SIZE", 7)

    result = file_operations.calculate_file_hash(sample_path)
    expected = hashlib.sha256(content).hexdigest()

    assert result == expected


def test_generate_target_path_logs_sanitizer_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sanitizer errors should be logged and result in a None target path."""

    base_path = Path("/music")

    class _FailingDirectoryGenerator:
        def generate(self, _metadata: TrackMetadata) -> Path:
            raise SanitizerError("directory sanitize failed")

    class _StubFileNameGenerator:
        def generate(self, _metadata: TrackMetadata) -> str:
            return "ignored.mp3"

    metadata = TrackMetadata(title="Song", album_artist="Artist")

    caplog.set_level("ERROR")

    result = file_operations.generate_target_path(
        base_path,
        directory_generator=cast(
            DirectoryGenerator,
            cast(object, _FailingDirectoryGenerator()),
        ),
        file_name_generator=cast(
            FileNameGenerator,
            cast(object, _StubFileNameGenerator()),
        ),
        metadata=metadata,
    )

    assert result is None
    assert any("Sanitization failed" in message for message in caplog.messages)
