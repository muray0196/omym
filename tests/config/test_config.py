"""Test configuration management."""

from pathlib import Path

import pytest

from omym.config.config import Config
from omym.config.paths import default_config_path


@pytest.fixture
def repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Force portable repo root to a temporary directory for isolation."""
    # Create repo markers so _detect_repo_root() returns tmp_path
    _ = (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname='tmp'\n")
    # Monkeypatch the detector to be explicit and fast
    import omym.config.paths as p

    def _fake_detect_repo_root(_start: Path | None = None) -> Path:
        return tmp_path

    monkeypatch.setattr(p, "_detect_repo_root", _fake_detect_repo_root, raising=True)
    return tmp_path


def test_default_config(repo_root: Path) -> None:
    _ = repo_root  # acknowledge fixture usage
    """Test default configuration creation at portable repo location."""
    config = Config()
    assert config.base_path is None
    assert config.log_file is None
    # Ensure save creates file in XDG default path
    config.save()
    assert default_config_path().exists()


def test_save_load_toml(repo_root: Path) -> None:
    _ = repo_root  # acknowledge fixture usage
    """Test saving and loading configuration in TOML format at repo path."""
    # Create and save config
    original_config = Config(
        base_path=Path("/test/music"),
        log_file=Path("/test/logs/omym.log"),
    )
    original_config.save()

    # Load config (reset singleton first)
    Config._instance = None  # pyright: ignore[reportPrivateUsage] - reset singleton for test
    loaded_config = Config.load()

    # Verify values
    assert loaded_config.base_path == Path("/test/music")
    assert loaded_config.log_file == Path("/test/logs/omym.log")
    assert default_config_path().exists()


def test_save_load_none_values(repo_root: Path) -> None:
    _ = repo_root  # acknowledge fixture usage
    """Test saving and loading configuration with None values."""
    # Create and save config with None values
    original_config = Config(
        base_path=None,
        log_file=None,
    )
    original_config.save()

    # Load config (reset singleton first)
    Config._instance = None  # pyright: ignore[reportPrivateUsage] - reset singleton for test
    loaded_config = Config.load()

    # Verify values
    assert loaded_config.base_path is None
    assert loaded_config.log_file is None


def test_singleton_behavior(repo_root: Path) -> None:
    _ = repo_root  # acknowledge fixture usage
    """Test singleton pattern behavior with fixed XDG path."""
    # Create first instance
    config1 = Config.load()
    config1.base_path = Path("/test/music1")
    config1.save()

    # Load second instance (should be same object)
    config2 = Config.load()
    assert config2 is config1
    assert config2.base_path == Path("/test/music1")


def test_toml_comments(repo_root: Path) -> None:
    _ = repo_root  # acknowledge fixture usage
    """Test TOML file contains comments."""
    config = Config(
        base_path=Path("/test/music"),
    )
    config.save()

    # Read the raw TOML file
    with open(default_config_path(), "r", encoding="utf-8") as f:
        content = f.read()

    # Verify comments exist
    assert "# OMYM Configuration File" in content
    assert "# Base path for your music library" in content
    assert "# Log file path" in content
