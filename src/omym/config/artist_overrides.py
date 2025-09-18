"""Artist override configuration loader using TOML."""

from __future__ import annotations

import os
import textwrap
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from omym.config.paths import default_artist_overrides_path
from omym.infra.logger.logger import logger

_ARTIST_OVERRIDES_ENV = "OMYM_ARTIST_OVERRIDES_PATH"
_DEFAULT_METADATA_VERSION = 1

_TEMPLATE = textwrap.dedent(
    """
    # Artist override configuration (TOML)
    #
    # Values remain empty until you provide a preferred romanised name.
    # Entries are appended automatically after romanisation runs during dry-run or organise.

    metadata_version = 1

    [defaults]
    # Example: locale = "en_US"

    [overrides]
    # Automatically populated artist entries will appear here.
    """
).strip() + "\n"


class ArtistOverridesError(Exception):
    """Base exception for artist override configuration errors."""


class ArtistOverridesParseError(ArtistOverridesError):
    """Raised when the TOML document cannot be parsed."""


class ArtistOverridesValidationError(ArtistOverridesError):
    """Raised when the parsed document is semantically invalid."""


@dataclass(slots=True)
class ArtistOverrideStore:
    """In-memory representation of configured artist overrides."""

    metadata_version: int = _DEFAULT_METADATA_VERSION
    overrides: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    _normalized: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize overrides for case-insensitive lookups."""

        self.metadata_version = max(int(self.metadata_version), _DEFAULT_METADATA_VERSION)
        self.defaults = {
            key.strip(): value.strip() for key, value in self.defaults.items()
        }

        normalized: dict[str, str] = {}
        cleaned: dict[str, str] = {}

        for key, value in self.overrides.items():
            trimmed_key = key.strip()
            trimmed_value = value.strip()
            if not trimmed_key:
                raise ArtistOverridesValidationError("Override keys must not be empty")

            lowered = trimmed_key.casefold()
            if lowered in normalized:
                raise ArtistOverridesValidationError(
                    f"Duplicate override detected for '{trimmed_key}'"
                )

            if trimmed_value:
                normalized[lowered] = trimmed_value
                cleaned[trimmed_key] = trimmed_value
            else:
                cleaned[trimmed_key] = ""

        self.overrides = cleaned
        self._normalized = normalized

    def resolve(self, raw_artist: str | None) -> str | None:
        """Return the canonical override for ``raw_artist`` if configured."""

        if raw_artist is None:
            return None

        trimmed = raw_artist.strip()
        if not trimmed:
            return None

        value = self._normalized.get(trimmed.casefold())
        return value or None

    def is_empty(self) -> bool:
        """Return whether no overrides are configured."""

        return not self._normalized

    def snapshot(self) -> dict[str, str]:
        """Return a copy of the overrides for inspection or testing."""

        return dict(self.overrides)

    def add_placeholder(self, raw_artist: str) -> bool:
        """Ensure an override entry exists for the given artist with an empty value."""

        trimmed = raw_artist.strip()
        if not trimmed:
            return False

        lowered = trimmed.casefold()
        if lowered in self._normalized:
            return False

        self.overrides[trimmed] = ""
        self._normalized[lowered] = ""
        return True


@dataclass(slots=True)
class ArtistOverrideRepository:
    """Repository wrapper that persists artist override entries."""

    path: Path
    store: ArtistOverrideStore

    def resolve(self, raw_artist: str | None) -> str | None:
        return self.store.resolve(raw_artist)

    def ensure_placeholder(self, raw_artist: str) -> None:
        if self.store.add_placeholder(raw_artist):
            self._persist()

    def snapshot(self) -> dict[str, str]:
        return self.store.snapshot()

    def _persist(self) -> None:
        lines: list[str] = [
            "# Artist override configuration (TOML)",
            "#",
            "# Values remain empty until you provide a preferred romanised name.",
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
        lines.append("[overrides]")

        if self.store.overrides:
            for key in sorted(self.store.overrides, key=str.casefold):
                value = self._quote(self.store.overrides[key])
                quoted_key = self._quote(key)
                lines.append(f"{quoted_key} = {value}")
        else:
            lines.append("# Automatically populated artist entries will appear here.")

        lines.append("")

        content = "\n".join(lines)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _ = self.path.write_text(content, encoding="utf-8")

    @staticmethod
    def _quote(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
        return f'"{escaped}"'


def load_artist_overrides(
    *, path: Path | None = None, env: Mapping[str, str] | None = None
) -> ArtistOverrideRepository:
    """Load artist overrides from configuration.

    Args:
        path: Optional explicit path to the overrides file.
        env: Optional environment mapping to read configuration from.

    Returns:
        ArtistOverrideStore: Loaded overrides (possibly empty).
    """

    resolved_path = _resolve_configuration_path(path=path, env=env)
    if not resolved_path.exists():
        _write_template(resolved_path)
        logger.info("Created artist override template at %s", resolved_path)
        return ArtistOverrideRepository(
            path=resolved_path,
            store=ArtistOverrideStore(),
        )

    try:
        with resolved_path.open("rb") as handle:
            document = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ArtistOverridesParseError(
            f"Invalid TOML in artist override file: {resolved_path}"
        ) from exc
    except OSError as exc:  # pragma: no cover - rare filesystem failure
        raise ArtistOverridesError(
            f"Failed to read artist override file: {resolved_path}"
        ) from exc

    metadata_version = _extract_metadata_version(document)
    defaults = _extract_string_table(document.get("defaults", {}), section="defaults")
    overrides = _extract_string_table(document.get("overrides", {}), section="overrides")

    store = ArtistOverrideStore(
        metadata_version=metadata_version,
        defaults=defaults,
        overrides=overrides,
    )

    repository = ArtistOverrideRepository(path=resolved_path, store=store)

    if store.is_empty():
        logger.info("Artist override file loaded but no entries defined: %s", resolved_path)
    else:
        logger.info(
            "Loaded %d artist override entries from %s",
            len(store.snapshot()),
            resolved_path,
        )

    return repository


def _resolve_configuration_path(
    *, path: Path | None, env: Mapping[str, str] | None
) -> Path:
    if path is not None:
        return path.expanduser().resolve()

    env_mapping = env if env is not None else os.environ
    candidate = env_mapping.get(_ARTIST_OVERRIDES_ENV) or ""
    candidate = candidate.strip()
    if candidate:
        return Path(candidate).expanduser().resolve()

    return default_artist_overrides_path()


def _write_template(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(_TEMPLATE, encoding="utf-8")


def _extract_metadata_version(document: Mapping[str, Any]) -> int:
    value = document.get("metadata_version", _DEFAULT_METADATA_VERSION)
    if not isinstance(value, int) or value < 1:
        raise ArtistOverridesValidationError("metadata_version must be a positive integer")
    return value


def _extract_string_table(table: Any, *, section: str) -> dict[str, str]:
    if table is None:
        return {}
    if not isinstance(table, dict):
        raise ArtistOverridesValidationError(f"{section} section must be a table")

    table_dict = cast(dict[object, Any], table)
    result: dict[str, str] = {}
    for key_obj, value in table_dict.items():
        if not isinstance(key_obj, str):
            raise ArtistOverridesValidationError(f"{section} keys must be strings")
        key = key_obj
        if not isinstance(value, str):
            raise ArtistOverridesValidationError(
                f"{section} value for '{key}' must be a string"
            )
        result[key] = value
    return result


__all__ = [
    "ArtistOverrideStore",
    "ArtistOverrideRepository",
    "ArtistOverridesError",
    "ArtistOverridesParseError",
    "ArtistOverridesValidationError",
    "load_artist_overrides",
]
