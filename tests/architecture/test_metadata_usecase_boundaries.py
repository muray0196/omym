"""
Summary: Architecture checks ensuring metadata use cases stay isolated from platform persistence.
Why: Prevent regressions where use case modules import platform database layers directly.
"""

from __future__ import annotations

from pathlib import Path


def test_metadata_usecases_do_not_import_platform_db() -> None:
    """Ensure metadata use case modules avoid depending on platform database code."""

    repo_root = Path(__file__).resolve().parents[2]
    usecases_dir = repo_root / "src" / "omym" / "features" / "metadata" / "usecases"
    offending_files: list[Path] = []
    for path in usecases_dir.rglob("*.py"):
        contents = path.read_text(encoding="utf-8")
        if "omym.platform.db" in contents:
            offending_files.append(path)
    assert offending_files == [], (
        "Use case modules must not import platform database packages; found in: "
        f"{', '.join(str(path.relative_to(repo_root)) for path in offending_files)}"
    )


def test_metadata_usecases_do_not_import_path_feature() -> None:
    """Ensure metadata use cases remain decoupled from the path feature renamer helpers."""

    repo_root = Path(__file__).resolve().parents[2]
    usecases_dir = repo_root / "src" / "omym" / "features" / "metadata" / "usecases"
    offending_files: list[Path] = []
    for path in usecases_dir.rglob("*.py"):
        contents = path.read_text(encoding="utf-8")
        if "omym.features.path" in contents:
            offending_files.append(path)
    assert offending_files == [], (
        "Metadata use cases must depend on renamer ports via adapters; found path imports in: "
        f"{', '.join(str(path.relative_to(repo_root)) for path in offending_files)}"
    )
