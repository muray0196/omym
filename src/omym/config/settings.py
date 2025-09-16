"""Environment-based runtime settings for OMYM.

This module provides simple, typed settings loaded from environment
variables. It intentionally avoids any I/O or global mutable state beyond
reading environment variables on import so that it remains side-effect free
and fast to import.

All names and behavior follow the project rules:
- Configuration via environment variables
- Explicit type hints and Google-style docstrings
"""

from __future__ import annotations

import os

from omym.config.config import config as app_config

# Core feature switches -------------------------------------------------------

def _env_bool(name: str) -> bool | None:
    """Read a boolean-like environment variable."""

    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


# Whether to attempt romanization via MusicBrainz. Falls back to configuration
# when the environment variable is unset.
_env_use_mb = _env_bool("OMYM_USE_MB_ROMANIZATION")
USE_MB_ROMANIZATION: bool = (
    _env_use_mb if _env_use_mb is not None else getattr(app_config, "use_mb_romanization", True)
)


# MusicBrainz application identity ------------------------------------------

# MusicBrainz recommends a User-Agent of the form:
#   "AppName/AppVersion (contact-url-or-email)"
# See: https://musicbrainz.org/doc/MusicBrainz_API/Best_Practices#User-Agent

MB_APP_NAME: str = os.getenv("OMYM_MB_APP_NAME", "omym")
MB_APP_VERSION: str = os.getenv("OMYM_MB_APP_VERSION", "0.1.0")
MB_CONTACT: str = os.getenv("OMYM_MB_CONTACT", "")


__all__ = [
    "USE_MB_ROMANIZATION",
    "MB_APP_NAME",
    "MB_APP_VERSION",
    "MB_CONTACT",
]
