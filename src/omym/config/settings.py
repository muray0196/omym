"""Where: src/omym/config/settings.py
What: Derived runtime settings sourced from persisted configuration.
Why: Expose validated constants to feature layers without file I/O.
Assumptions: - Config defaults remain compatible with current runtime expectations.
Trade-offs: - Validation is limited to simple boundary checks for speed.
"""

from __future__ import annotations

from omym.config.config import (
    ARTIST_ID_MAX_LENGTH_DEFAULT,
    FILE_HASH_CHUNK_SIZE_DEFAULT,
    config as app_config,
)

# Core feature switches -------------------------------------------------------

# Whether to attempt romanization via MusicBrainz (config-driven only).
USE_MB_ROMANIZATION: bool = bool(getattr(app_config, "use_mb_romanization", True))


# MusicBrainz application identity ------------------------------------------

# Language codes reported by langid that indicate non-Latin results from
# MusicBrainz. These codes align with the languages we request romanization
# for and are used to keep caches free of non-Latin values.
MB_NON_LATIN_LANG_CODES: tuple[str, ...] = ("ja", "zh")


# MusicBrainz recommends a User-Agent of the form:
#   "AppName/AppVersion (contact-url-or-email)"
# See: https://musicbrainz.org/doc/MusicBrainz_API/Best_Practices#User-Agent

MB_APP_NAME: str = app_config.mb_app_name or "omym"
MB_APP_VERSION: str = app_config.mb_app_version or "0.1.0"
MB_CONTACT: str = app_config.mb_contact or ""

# Directory name for collecting unprocessed files under a source root.
UNPROCESSED_DIR_NAME: str = app_config.unprocessed_dir_name or "!unprocessed"

_preview_limit = getattr(app_config, "unprocessed_preview_limit", 5)
UNPROCESSED_PREVIEW_LIMIT: int = _preview_limit if _preview_limit >= 0 else 0

_file_hash_chunk_size = getattr(app_config, "file_hash_chunk_size", FILE_HASH_CHUNK_SIZE_DEFAULT)
FILE_HASH_CHUNK_SIZE: int = (
    _file_hash_chunk_size if _file_hash_chunk_size > 0 else FILE_HASH_CHUNK_SIZE_DEFAULT
)


_artist_id_max = getattr(app_config, "artist_id_max_length", ARTIST_ID_MAX_LENGTH_DEFAULT)
ARTIST_ID_MAX_LENGTH: int = (
    _artist_id_max
    if isinstance(_artist_id_max, int) and _artist_id_max > 0
    else ARTIST_ID_MAX_LENGTH_DEFAULT
)


__all__ = [
    "USE_MB_ROMANIZATION",
    "MB_APP_NAME",
    "MB_APP_VERSION",
    "MB_CONTACT",
    "UNPROCESSED_DIR_NAME",
    "UNPROCESSED_PREVIEW_LIMIT",
    "MB_NON_LATIN_LANG_CODES",
    "FILE_HASH_CHUNK_SIZE",
    "ARTIST_ID_MAX_LENGTH",
]
