"""Where: tests/features/metadata/usecases/test_file_operations.py
What: Regression tests for file hashing behaviour in metadata use cases.
Why: Ensure hashing results stay stable when chunk sizing is configurable.
Assumptions: - hashlib.sha256 remains deterministic for identical inputs.
Trade-offs: - Uses monkeypatch to override module constant instead of config reload.
"""

from __future__ import annotations

import hashlib

from pathlib import Path

import pytest

from omym.features.metadata.usecases.file_management import file_operations


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
