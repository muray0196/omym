"""Configuration management for OMYM."""

import json
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, ClassVar, Dict, Any

from omym.utils.logger import logger


def _path_field(default: Optional[Path] = None) -> Any:
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
    base_path: Optional[Path] = _path_field()

    # Log file path
    log_file: Optional[Path] = _path_field()

    # Default configuration file path (relative to project root)
    config_file: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "config" / "config.toml"
    )

    # Singleton instance
    _instance: ClassVar[Optional["Config"]] = None
    _loaded_from: ClassVar[Optional[Path]] = None

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
            elif value is None:
                config_dict[key] = ""  # Empty string for None values

        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # If the file exists and is JSON, convert it to TOML
            if self.config_file.suffix == '.json':
                # Create new TOML path
                toml_path = self.config_file.with_suffix('.toml')
                # Write as TOML
                self._save_toml(toml_path, config_dict)
                # Remove old JSON file if it exists
                if self.config_file.exists():
                    self.config_file.unlink()
                # Update config_file path
                self.config_file = toml_path
                logger.info("Converted configuration from JSON to TOML: %s", toml_path)
            else:
                # Save as TOML with comments
                self._save_toml(self.config_file, config_dict)
                logger.info("Configuration saved to %s", self.config_file)
        except Exception as e:
            logger.error("Failed to save configuration: %s", e)
            raise

    def _save_toml(self, path: Path, config: Dict[str, Any]) -> None:
        """Save configuration as TOML with comments.

        Args:
            path: Path to save the configuration to
            config: Configuration dictionary to save
        """
        toml_str = "# OMYM Configuration File\n\n"
        toml_str += "# Base path for your music library (optional)\n"
        toml_str += "# This is the root directory where your music files are stored\n"
        toml_str += "# Example: base_path = \"/path/to/your/music\"\n"
        toml_str += f'base_path = {self._format_toml_value(config["base_path"])}\n\n'
        toml_str += "# Log file path (optional)\n"
        toml_str += "# Where to store the application logs\n"
        toml_str += "# Example: log_file = \"/path/to/logs/omym.log\"\n"
        toml_str += f'log_file = {self._format_toml_value(config["log_file"])}\n\n'
        toml_str += "# Configuration file path (relative to project root)\n"
        toml_str += "# Location of this configuration file\n"
        toml_str += f'config_file = "{config["config_file"]}"\n'

        with open(path, "w", encoding="utf-8") as f:
            f.write(toml_str)

    def _format_toml_value(self, value: Any) -> str:
        """Format a value for TOML serialization.

        Args:
            value: Value to format

        Returns:
            str: Formatted value
        """
        if value is None or value == "":
            return '""'  # Empty string for None values
        if isinstance(value, (str, Path)):
            return f'"{str(value)}"'
        return str(value)

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "Config":
        """Load configuration from file.

        Args:
            config_file: Optional path to config file. If None, uses default path.

        Returns:
            Config: Loaded configuration object.
        """
        # If config is already loaded from the same file, return cached instance
        if cls._instance is not None:
            if config_file is None or config_file == cls._loaded_from:
                return cls._instance
            # If a different config file is requested, clear the cache
            cls._instance = None
            cls._loaded_from = None

        if config_file is None:
            config_file = cls().config_file

        try:
            if config_file.exists():
                # Try loading as TOML first
                try:
                    with open(config_file, "rb") as f:
                        config_dict = tomllib.load(f)
                except Exception:
                    # If TOML loading fails, try JSON as fallback
                    if config_file.suffix == '.json':
                        with open(config_file, "r", encoding="utf-8") as f:
                            config_dict = json.load(f)
                        logger.info("Loaded legacy JSON configuration from %s", config_file)
                    else:
                        raise

                # Convert string paths back to Path objects and handle empty strings
                for key, value in config_dict.items():
                    if key.endswith("_path") or key.endswith("_dir") or key == "config_file":
                        if value and value.strip() != "":  # Convert only non-empty strings
                            config_dict[key] = str(value)  # Keep as string, let __post_init__ handle conversion
                        else:
                            config_dict[key] = None

                logger.info("Configuration loaded from %s", config_file)
                instance = cls(**config_dict)
                
                # Save immediately if it's a JSON file to trigger conversion
                if config_file.suffix == '.json':
                    instance.save()
                
                cls._instance = instance
                cls._loaded_from = instance.config_file  # Use the potentially updated config_file path
                return instance

            # If config file doesn't exist, create default config
            config = cls(config_file=config_file)
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
