"""Configuration management for OMYM."""
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from omym.infra.logger.logger import logger
from omym.config.paths import default_config_path


def _path_field(default: Path | None = None) -> Any:
    """Create a field for Path objects with proper conversion.

    Args:
        default: Default value for the field.

    Returns:
        Field with proper metadata for path handling.
    """
    return field(default=default, metadata={"path": True})


@dataclass
class Config:
    """Application configuration."""

    # Base path for music library
    base_path: Path | None = _path_field()

    # Log file path
    log_file: Path | None = _path_field()

    # Note: Configuration file path is fixed by policy (XDG). Users cannot
    # override it via config values. See default_config_path().

    # Singleton instance
    _instance: ClassVar["Config | None"] = None
    _loaded_from: ClassVar[Path | None] = None

    def __post_init__(self) -> None:
        """Convert string paths to Path objects after initialization."""
        for field_name, field_type in self.__annotations__.items():
            value = getattr(self, field_name)
            if isinstance(value, str) and "Path" in str(field_type):
                setattr(self, field_name, Path(value) if value else None)

    def save(self) -> None:
        """Save configuration to file."""
        config_dict = asdict(self)

        # Convert Path objects to strings for serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)

        try:
            # If the file exists and is JSON, convert it to TOML
            # Save as TOML with comments at default XDG path
            target = default_config_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            self._save_toml(target, config_dict)
            logger.info("Configuration saved to %s", target)
        except Exception as e:
            logger.error("Failed to save configuration: %s", e)
            raise

    def _save_toml(self, path: Path, config: dict[str, Any]) -> None:
        """Save configuration as TOML with comments.

        Args:
            path: Path to save the configuration to
            config: Configuration dictionary to save
        """
        toml_str = "# OMYM Configuration File\n\n"

        # Base path section
        toml_str += "# Base path for your music library (optional)\n"
        toml_str += "# This is the root directory where your music files are stored\n"
        toml_str += '# Example: base_path = "/path/to/your/music"\n'
        if config["base_path"] is not None:
            toml_str += f"base_path = {self._format_toml_value(config['base_path'])}\n"
        toml_str += "\n"

        # Log file section
        toml_str += "# Log file path (optional)\n"
        toml_str += "# Where to store the application logs\n"
        toml_str += '# Example: log_file = "/path/to/logs/omym.log"\n'
        if config["log_file"] is not None:
            toml_str += f"log_file = {self._format_toml_value(config['log_file'])}\n"
        toml_str += "\n"

        # No explicit config_file is stored; path is fixed by policy.

        with open(path, "w", encoding="utf-8") as f:
            _ = f.write(toml_str)  # Assign to _ to acknowledge unused result

    def _format_toml_value(self, value: Any) -> str:
        """Format a value for TOML serialization.

        Args:
            value: Value to format

        Returns:
            str: Formatted value
        """
        if isinstance(value, (str, Path)):
            return f'"{str(value)}"'
        return str(value)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file.

        Args:
            None

        Returns:
            Config: Loaded configuration object.
        """
        # If config is already loaded from the same file, return cached instance
        if cls._instance is not None:
            return cls._instance

        config_file = default_config_path()

        try:
            if config_file.exists():
                # Try loading as TOML first
                try:
                    with open(config_file, "rb") as f:
                        config_dict = tomllib.load(f)
                except Exception:
                    raise

                # Convert string paths back to Path objects and handle empty strings
                for key, value in config_dict.items():
                    if key.endswith("_path") or key.endswith("_dir"):
                        if value and value.strip() != "":  # Convert only non-empty strings
                            config_dict[key] = str(value)  # Keep as string, let __post_init__ handle conversion
                        else:
                            config_dict[key] = None

                logger.info("Configuration loaded from %s", config_file)
                instance = cls(**config_dict)

                cls._instance = instance
                cls._loaded_from = config_file
                return instance

            # If config file doesn't exist, create default config
            config = cls()
            config.save()
            logger.info("Created default configuration at %s", config_file)
            cls._instance = config
            cls._loaded_from = config_file
            return config

        except Exception as e:
            logger.error("Failed to load configuration: %s", e)
            raise


# Global configuration instance
config = Config.load()
