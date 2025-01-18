"""Test configuration management."""

import json
from pathlib import Path

import pytest

from omym.config import Config


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a temporary config file.

    Args:
        tmp_path: Temporary directory path fixture.

    Returns:
        Path: Path to the temporary config file.
    """
    return tmp_path / "config.toml"


def test_default_config(config_file: Path) -> None:
    """Test default configuration creation."""
    config = Config(config_file=config_file)
    assert config.base_path is None
    assert config.log_file is None
    assert config.config_file == config_file


def test_save_load_toml(config_file: Path) -> None:
    """Test saving and loading configuration in TOML format."""
    # Create and save config
    original_config = Config(
        base_path=Path("/test/music"),
        log_file=Path("/test/logs/omym.log"),
        config_file=config_file,
    )
    original_config.save()

    # Load config
    loaded_config = Config.load(config_file)

    # Verify values
    assert loaded_config.base_path == Path("/test/music")
    assert loaded_config.log_file == Path("/test/logs/omym.log")
    assert loaded_config.config_file == config_file


def test_save_load_none_values(config_file: Path) -> None:
    """Test saving and loading configuration with None values."""
    # Create and save config with None values
    original_config = Config(
        base_path=None,
        log_file=None,
        config_file=config_file,
    )
    original_config.save()

    # Load config
    loaded_config = Config.load(config_file)

    # Verify values
    assert loaded_config.base_path is None
    assert loaded_config.log_file is None
    assert loaded_config.config_file == config_file


def test_json_to_toml_conversion(tmp_path: Path) -> None:
    """Test conversion from JSON to TOML format."""
    # Create JSON config
    json_config = tmp_path / "config.json"
    config_data = {
        "base_path": "/test/music",
        "log_file": "/test/logs/omym.log",
        "config_file": str(json_config),
    }
    with open(json_config, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    # Load and save config (should convert to TOML)
    config = Config.load(json_config)
    assert config.base_path == Path("/test/music")
    assert config.log_file == Path("/test/logs/omym.log")

    # Verify JSON file is converted to TOML
    assert not json_config.exists()
    toml_config = json_config.with_suffix(".toml")
    assert toml_config.exists()

    # Load the converted TOML file
    converted_config = Config.load(toml_config)
    assert converted_config.base_path == Path("/test/music")
    assert converted_config.log_file == Path("/test/logs/omym.log")


def test_singleton_behavior(config_file: Path) -> None:
    """Test singleton pattern behavior."""
    # Create first instance
    config1 = Config.load(config_file)
    config1.base_path = Path("/test/music1")
    config1.save()

    # Load second instance (should be same object)
    config2 = Config.load(config_file)
    assert config2 is config1
    assert config2.base_path == Path("/test/music1")

    # Load with different path (should be new instance)
    new_config_file = config_file.parent / "other_config.toml"
    config3 = Config.load(new_config_file)
    assert config3 is not config1
    assert config3.base_path is None


def test_toml_comments(config_file: Path) -> None:
    """Test TOML file contains comments."""
    config = Config(
        base_path=Path("/test/music"),
        config_file=config_file,
    )
    config.save()

    # Read the raw TOML file
    with open(config_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify comments exist
    assert "# OMYM Configuration File" in content
    assert "# Base path for your music library" in content
    assert "# Log file path" in content 