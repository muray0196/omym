"""Runtime settings for OMYM sourced from the project config file."""

from __future__ import annotations

from omym.config.config import config as app_config

# Core feature switches -------------------------------------------------------

# Whether to attempt romanization via MusicBrainz (config-driven only).
USE_MB_ROMANIZATION: bool = bool(getattr(app_config, "use_mb_romanization", True))


# MusicBrainz application identity ------------------------------------------

# MusicBrainz recommends a User-Agent of the form:
#   "AppName/AppVersion (contact-url-or-email)"
# See: https://musicbrainz.org/doc/MusicBrainz_API/Best_Practices#User-Agent

MB_APP_NAME: str = app_config.mb_app_name or "omym"
MB_APP_VERSION: str = app_config.mb_app_version or "0.1.0"
MB_CONTACT: str = app_config.mb_contact or ""

# Directory name for collecting unprocessed files under a source root.
UNPROCESSED_DIR_NAME: str = app_config.unprocessed_dir_name or "!unprocessed"


__all__ = [
    "USE_MB_ROMANIZATION",
    "MB_APP_NAME",
    "MB_APP_VERSION",
    "MB_CONTACT",
    "UNPROCESSED_DIR_NAME",
]
