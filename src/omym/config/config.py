"""Configuration management for OMYM."""
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from omym.config.file_ops import write_text_file
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

    # MusicBrainz settings
    use_mb_romanization: bool = True
    mb_app_name: str | None = None
    mb_app_version: str | None = None
    mb_contact: str | None = None

    # Note: Configuration file path is fixed by policy (XDG). Users cannot
    # override it via config values. See default_config_path().

    # Singleton instance
    _instance: ClassVar["Config | None"] = None
    _loaded_from: ClassVar[Path | None] = None

    def __post_init__(self) -> None:
        """Convert string paths to ``Path`` objects using field metadata.

        This avoids brittle type-name introspection and leverages the
        ``metadata={"path": True}`` flag set by ``_path_field`` so only
        intended fields are converted.
        """
        from dataclasses import fields

        for f in fields(self):
            if not f.metadata.get("path", False):
                continue
            value = getattr(self, f.name)
            if isinstance(value, str):
                setattr(self, f.name, Path(value) if value else None)

    def save(self) -> None:
        """Save configuration to file."""
        config_dict = asdict(self)

        # Convert Path objects to strings for serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)

        try:
            # Save as TOML with comments at default portable path
            target = default_config_path()
            content = self._render_toml(config_dict)
            write_text_file(target, content)
            logger.info("Configuration saved to %s", target)
        except Exception as e:
            logger.error("Failed to save configuration: %s", e)
            raise

    def _render_toml(self, config: dict[str, Any]) -> str:
        """Render configuration as TOML with inline guidance."""

        lines: list[str] = []

        # Header
        lines.append("# OMYM Configuration File")
        lines.append("")

        # Base path section
        lines.append("# Base path for your music library (optional)")
        lines.append("# This is the root directory where your music files are stored")
        lines.append('# Example: base_path = "/path/to/your/music"')
        if config["base_path"] is not None:
            lines.append(f"base_path = {self._format_toml_value(config['base_path'])}")
        lines.append("")

        # Log file section
        lines.append("# Log file path (optional)")
        lines.append("# Where to store the application logs")
        lines.append('# Example: log_file = "/path/to/logs/omym.log"')
        if config["log_file"] is not None:
            lines.append(f"log_file = {self._format_toml_value(config['log_file'])}")
        lines.append("")

        # MusicBrainz romanization section
        lines.append("# MusicBrainz romanization (optional)")
        lines.append("# Set to true to resolve artist names via MusicBrainz (default true)")
        lines.append(
            f"use_mb_romanization = {self._format_toml_value(config['use_mb_romanization'])}"
        )
        lines.append("")

        # MusicBrainz identity
        lines.append("# MusicBrainz application identity (optional)")
        lines.append("# These fields override environment variables if provided")
        if config.get("mb_app_name"):
            lines.append(f"mb_app_name = {self._format_toml_value(config['mb_app_name'])}")
        if config.get("mb_app_version"):
            lines.append(f"mb_app_version = {self._format_toml_value(config['mb_app_version'])}")
        if config.get("mb_contact"):
            lines.append(f"mb_contact = {self._format_toml_value(config['mb_contact'])}")
        lines.append("")

        return "\n".join(lines)

    def _format_toml_value(self, value: Any) -> str:
        """Format a value for TOML serialization.

        Args:
            value: Value to format

        Returns:
            str: Formatted value
        """
        if isinstance(value, bool):
            return "true" if value else "false"
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

                # Ensure new fields have defaults if absent (backward compatibility)
                _ = config_dict.setdefault("use_mb_romanization", True)
                _ = config_dict.setdefault("mb_app_name", None)
                _ = config_dict.setdefault("mb_app_version", None)
                _ = config_dict.setdefault("mb_contact", None)

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
