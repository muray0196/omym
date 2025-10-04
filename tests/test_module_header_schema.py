"""
Summary: Validate Summary/Why header docstring schema for selected modules.
Why: Prevent regression to inconsistent header formats across touched files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

HEADER_OPEN: str = '"""'
HEADER_CLOSE: str = '"""'
SUMMARY_PREFIX: str = "Summary: "
WHY_PREFIX: str = "Why: "
SUMMARY_OFFSET: int = 1
WHY_OFFSET: int = 2
CLOSE_OFFSET: int = 3
HEADER_LENGTH: int = 4

TARGET_MODULES: tuple[Path, ...] = (
    Path("src/omym/features/path/__init__.py"),
    Path("src/omym/features/path/domain/sanitizer.py"),
    Path("src/omym/features/path/domain/path_elements.py"),
    Path("src/omym/features/path/usecases/path_generator.py"),
    Path("src/omym/features/path/usecases/ports.py"),
    Path("src/omym/features/path/usecases/renamer/filename.py"),
    Path("src/omym/features/path/usecases/renamer/directory.py"),
    Path("src/omym/features/path/usecases/renamer/artist_id.py"),
    Path("src/omym/features/path/usecases/renamer/cached_artist_id.py"),
    Path("src/omym/features/path/usecases/renamer/__init__.py"),
    Path("src/omym/features/metadata/usecases/processing/file_operations.py"),
    Path("tests/features/path/test_path_elements.py"),
    Path("tests/features/path/test_path_generator.py"),
    Path("tests/features/path/test_music_file_renamer.py"),
    Path("tests/features/metadata/usecases/test_file_operations.py"),
)


@pytest.mark.parametrize("module_path", TARGET_MODULES, ids=lambda path: str(path))
def test_module_headers_follow_summary_why_schema(module_path: Path) -> None:
    """Ensure module header docstring uses Summary and Why lines."""

    content_lines = module_path.read_text(encoding="utf-8").splitlines()
    start_index = next(
        (index for index, line in enumerate(content_lines) if line.strip()),
        None,
    )
    assert start_index is not None, f"{module_path} must not be empty"

    assert len(content_lines) >= start_index + HEADER_LENGTH, (
        f"{module_path} must provide at least {HEADER_LENGTH} header lines"
    )

    opening_line = content_lines[start_index].strip()
    assert opening_line == HEADER_OPEN, f"{module_path} must start with header docstring"

    summary_line = content_lines[start_index + SUMMARY_OFFSET]
    why_line = content_lines[start_index + WHY_OFFSET]
    closing_line = content_lines[start_index + CLOSE_OFFSET].strip()

    assert summary_line.startswith(SUMMARY_PREFIX), (
        f"{module_path} summary line must begin with '{SUMMARY_PREFIX}'"
    )
    assert why_line.startswith(WHY_PREFIX), (
        f"{module_path} why line must begin with '{WHY_PREFIX}'"
    )
    assert closing_line == HEADER_CLOSE, (
        f"{module_path} header must close with triple quotes"
    )

    assert summary_line.removeprefix(SUMMARY_PREFIX).strip(), (
        f"{module_path} summary text cannot be empty"
    )
    assert why_line.removeprefix(WHY_PREFIX).strip(), (
        f"{module_path} why text cannot be empty"
    )
