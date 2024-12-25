"""Configuration management for OMYM."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, ClassVar

from omym.utils.logger import logger


@dataclass
class Config:
    """Application configuration."""

    # Base path for music library
    base_path: Optional[Path] = None

    # Log file path
    log_file: Optional[Path] = None

    # Default configuration file path
    config_file: Path = field(
        default_factory=lambda: Path.home() / ".config" / "omym" / "config.json"
    )

    # Singleton instance
    _instance: ClassVar[Optional["Config"]] = None
    _loaded_from: ClassVar[Optional[Path]] = None

    def save(self) -> None:
        """Save configuration to file."""
        config_dict = asdict(self)

        # Convert Path objects to strings for JSON serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
            elif value is None:
                config_dict[key] = None

        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=4)
            logger.info("Configuration saved to %s", self.config_file)
        except Exception as e:
            logger.error("Failed to save configuration: %s", e)
            raise

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
                with open(config_file, "r", encoding="utf-8") as f:
                    config_dict = json.load(f)

                # Convert string paths back to Path objects
                for key, value in config_dict.items():
                    if key.endswith("_path") and value is not None:
                        config_dict[key] = Path(value)

                logger.info("Configuration loaded from %s", config_file)
                cls._instance = cls(**config_dict)
                cls._loaded_from = config_file
                return cls._instance

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
