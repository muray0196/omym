"""Tests for configuration path resolution helpers."""

from pathlib import Path

from omym.config.paths import default_log_dir, default_log_file


def test_default_log_paths(portable_repo_root: Path) -> None:
    """Default log locations should live under the repository logs/ folder."""

    _ = portable_repo_root
    expected_dir = portable_repo_root / "logs"
    assert default_log_dir() == expected_dir
    assert default_log_file() == expected_dir / "omym.log"
