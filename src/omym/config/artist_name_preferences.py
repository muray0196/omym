"""Artist name preference configuration loader using TOML."""

from __future__ import annotations

import textwrap
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from omym.config.file_ops import ensure_file_with_template, write_text_file
from omym.config.paths import (
    default_artist_name_preferences_path,
    resolve_overridable_path,
)
from omym.infra.logger.logger import logger

_ARTIST_NAME_PREFERENCES_ENV = "OMYM_ARTIST_NAME_PREFERENCES_PATH"
_DEFAULT_METADATA_VERSION = 1

_TEMPLATE = textwrap.dedent(
    """
    # Artist name preference configuration (TOML)
    #
    # Populate values with your preferred romanised names.
    # Entries are appended automatically after romanisation runs during dry-run or organise.

    metadata_version = 1

    [defaults]
    # Example: locale = "en_US"

    [preferences]
    # Automatically populated artist entries will appear here.
    """
).strip() + "\n"


class ArtistNamePreferenceError(Exception):
    """Base exception for artist name preference configuration errors."""


class ArtistNamePreferenceParseError(ArtistNamePreferenceError):
    """Raised when the TOML document cannot be parsed."""


class ArtistNamePreferenceValidationError(ArtistNamePreferenceError):
    """Raised when the parsed document is semantically invalid."""


@dataclass(slots=True)
class ArtistNamePreferenceStore:
    """In-memory representation of configured artist name preferences."""

    metadata_version: int = _DEFAULT_METADATA_VERSION
    preferences: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    _normalized: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize preferences for case-insensitive lookups."""

        self.metadata_version = max(int(self.metadata_version), _DEFAULT_METADATA_VERSION)
        self.defaults = {
            key.strip(): value.strip() for key, value in self.defaults.items()
        }

        normalized: dict[str, str] = {}
        cleaned: dict[str, str] = {}

        for key, value in self.preferences.items():
            trimmed_key = key.strip()
            trimmed_value = value.strip()
            if not trimmed_key:
                raise ArtistNamePreferenceValidationError(
                    "Preference keys must not be empty"
                )

            lowered = trimmed_key.casefold()
            if lowered in normalized:
                raise ArtistNamePreferenceValidationError(
                    f"Duplicate preference detected for '{trimmed_key}'"
                )

            if trimmed_value:
                normalized[lowered] = trimmed_value
                cleaned[trimmed_key] = trimmed_value
            else:
                cleaned[trimmed_key] = ""

        self.preferences = cleaned
        self._normalized = normalized

    def resolve(self, raw_artist: str | None) -> str | None:
        """Return the preferred name for ``raw_artist`` if configured."""

        if raw_artist is None:
            return None

        trimmed = raw_artist.strip()
        if not trimmed:
            return None

        value = self._normalized.get(trimmed.casefold())
        return value or None

    def is_empty(self) -> bool:
        """Return whether no preferences are configured."""

        return not self._normalized

    def snapshot(self) -> dict[str, str]:
        """Return a copy of the preferences for inspection or testing."""

        return dict(self.preferences)

    def add_placeholder(self, raw_artist: str) -> bool:
        """Ensure a preference entry exists for the given artist with an empty value."""

        trimmed = raw_artist.strip()
        if not trimmed:
            return False

        lowered = trimmed.casefold()
        if lowered in self._normalized:
            return False

        self.preferences[trimmed] = ""
        self._normalized[lowered] = ""
        return True


@dataclass(slots=True)
class ArtistNamePreferenceRepository:
    """Repository wrapper that persists artist name preference entries."""

    path: Path
    store: ArtistNamePreferenceStore

    def resolve(self, raw_artist: str | None) -> str | None:
        return self.store.resolve(raw_artist)

    def ensure_placeholder(self, raw_artist: str) -> None:
        if self.store.add_placeholder(raw_artist):
            self._persist()

    def snapshot(self) -> dict[str, str]:
        return self.store.snapshot()

    def _persist(self) -> None:
        lines: list[str] = [
            "# Artist name preference configuration (TOML)",
            "#",
            "# Populate values with your preferred romanised names.",
            "# Entries are appended automatically after romanisation runs during dry-run or organise.",
            "",
            f"metadata_version = {self.store.metadata_version}",
            "",
            "[defaults]",
        ]

        if self.store.defaults:
            for key in sorted(self.store.defaults):
                value = self._quote(self.store.defaults[key])
                lines.append(f"{key} = {value}")
        else:
            lines.append("# Example: locale = \"en_US\"")

        lines.append("")
        lines.append("[preferences]")

        if self.store.preferences:
            for key in sorted(self.store.preferences, key=str.casefold):
                value = self._quote(self.store.preferences[key])
                quoted_key = self._quote(key)
                lines.append(f"{quoted_key} = {value}")
        else:
            lines.append("# Automatically populated artist entries will appear here.")

        lines.append("")

        content = "\n".join(lines)
        write_text_file(self.path, content)

    @staticmethod
    def _quote(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
        return f'"{escaped}"'


def load_artist_name_preferences(
    *, path: Path | None = None, env: Mapping[str, str] | None = None
) -> ArtistNamePreferenceRepository:
    """Load artist name preferences from configuration.

    Args:
        path: Optional explicit path to the preferences file.
        env: Optional environment mapping to read configuration from.

    Returns:
        ArtistNamePreferenceRepository: Loaded preferences (possibly empty).
    """

    resolved_path = resolve_overridable_path(
        explicit_path=path,
        env=env,
        env_var=_ARTIST_NAME_PREFERENCES_ENV,
        default_factory=default_artist_name_preferences_path,
    )
    if ensure_file_with_template(
        resolved_path, template_provider=lambda: _TEMPLATE
    ):
        logger.info("Created artist name preference template at %s", resolved_path)
        return ArtistNamePreferenceRepository(
            path=resolved_path,
            store=ArtistNamePreferenceStore(),
        )

    try:
        with resolved_path.open("rb") as handle:
            document = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ArtistNamePreferenceParseError(
            f"Invalid TOML in artist name preference file: {resolved_path}"
        ) from exc
    except OSError as exc:  # pragma: no cover - rare filesystem failure
        raise ArtistNamePreferenceError(
            f"Failed to read artist name preference file: {resolved_path}"
        ) from exc

    metadata_version = _extract_metadata_version(document)
    defaults = _extract_string_table(document.get("defaults", {}), section="defaults")
    preferences = _extract_string_table(
        document.get("preferences", {}), section="preferences"
    )

    store = ArtistNamePreferenceStore(
        metadata_version=metadata_version,
        defaults=defaults,
        preferences=preferences,
    )

    repository = ArtistNamePreferenceRepository(path=resolved_path, store=store)

    if store.is_empty():
        logger.info(
            "Artist name preference file loaded but no entries defined: %s",
            resolved_path,
        )
    else:
        logger.info(
            "Loaded %d artist name preference entries from %s",
            len(store.snapshot()),
            resolved_path,
        )

    return repository


def _extract_metadata_version(document: Mapping[str, Any]) -> int:
    value = document.get("metadata_version", _DEFAULT_METADATA_VERSION)
    if not isinstance(value, int) or value < 1:
        raise ArtistNamePreferenceValidationError(
            "metadata_version must be a positive integer"
        )
    return value


def _extract_string_table(table: Any, *, section: str) -> dict[str, str]:
    if table is None:
        return {}
    if not isinstance(table, dict):
        raise ArtistNamePreferenceValidationError(f"{section} section must be a table")

    table_dict = cast(dict[object, Any], table)
    result: dict[str, str] = {}
    for key_obj, value in table_dict.items():
        if not isinstance(key_obj, str):
            raise ArtistNamePreferenceValidationError(f"{section} keys must be strings")
        key = key_obj
        if not isinstance(value, str):
            raise ArtistNamePreferenceValidationError(
                f"{section} value for '{key}' must be a string"
            )
        result[key] = value
    return result


__all__ = [
    "ArtistNamePreferenceStore",
    "ArtistNamePreferenceRepository",
    "ArtistNamePreferenceError",
    "ArtistNamePreferenceParseError",
    "ArtistNamePreferenceValidationError",
    "load_artist_name_preferences",
]
