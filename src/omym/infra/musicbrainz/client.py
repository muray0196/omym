"""MusicBrainz WS2 client helpers.

This module implements a tiny HTTP client for the MusicBrainz WS2 API to
search artists and extract a romanized name. It prefers an alias that has
``locale == 'ja-Latn'`` and ``primary == true`` and falls back to the
artist's ``sort-name``.

Design goals:
- Use ``requests`` when available; otherwise gracefully fall back to
  ``urllib.request`` (stdlib). This keeps the project portable without
  adding dependencies while still honoring the user's preference for
  ``requests`` when present.
- Provide a simple rate limiter: at least one second between requests and
  honor ``Retry-After`` headers (parsed as delta-seconds or HTTP-date) with
  a single retry.
- Any HTTP or JSON error is logged at WARNING level and results in ``None``.

The exposed API is ``fetch_romanized_name``.
"""

from __future__ import annotations

import json
import os
import time
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Final, Protocol

from omym.infra.logger.logger import logger
from omym.config.settings import MB_APP_NAME, MB_APP_VERSION, MB_CONTACT


# --- Rate limit primitives -------------------------------------------------

_RATE_LIMIT_LOCK: Final = threading.Lock()
_last_request_mono: float = 0.0
_MIN_INTERVAL_SECONDS: Final[float] = 1.0


def _respect_rate_limit() -> None:
    """Sleep to maintain a minimal interval between requests.

    Ensures at least ``_MIN_INTERVAL_SECONDS`` between consecutive starts of
    outgoing HTTP requests from this module. Thread-safe.
    """
    global _last_request_mono
    with _RATE_LIMIT_LOCK:
        now = time.monotonic()
        elapsed = now - _last_request_mono
        wait = _MIN_INTERVAL_SECONDS - elapsed
        if wait > 0:
            time.sleep(wait)
        _last_request_mono = time.monotonic()


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header value into seconds.

    Args:
        value: Header value which may be delta-seconds (e.g. ``"3"``) or an
            HTTP-date.

    Returns:
        Seconds to wait as float, or ``None`` if parsing fails or value is
        not provided.
    """
    if not value:
        return None
    value = value.strip()
    # Try delta-seconds
    if value.isdigit():
        return float(int(value))
    # Try HTTP-date
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    # Defensive: in some environments older helpers may return None
    if dt is None:  # pyright: ignore[reportUnnecessaryComparison] - intentional defensive check
        return None
    if dt.tzinfo is None:
        # Assume UTC if timezone is missing
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (dt - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delta)


# --- HTTP helpers ----------------------------------------------------------

MB_BASE_URL: Final[str] = "https://musicbrainz.org/ws/2/artist/"


class _RomanizationCache(Protocol):
    def get_romanized_name(self, artist_name: str) -> str | None:
        ...

    def upsert_romanized_name(
        self,
        artist_name: str,
        romanized_name: str,
        source: str | None = None,
    ) -> bool:
        ...


_client_ua: str | None = None
_romanization_cache: _RomanizationCache | None = None


def _user_agent() -> str:
    """Return a user agent string for MusicBrainz etiquette.

    Priority:
    1) A user agent prepared by ``MusicBrainzClient`` at module init time.
    2) ``MUSICBRAINZ_USER_AGENT`` environment variable if set.
    3) A generic fallback using the configured app name/version without contact.
    """
    if _client_ua:
        return _client_ua
    env = os.getenv("MUSICBRAINZ_USER_AGENT")
    if env:
        return env
    return f"{MB_APP_NAME}/{MB_APP_VERSION}"


@dataclass(slots=True)
class _HTTPResult:
    status: int
    headers: dict[str, str]
    data: dict[str, Any] | None


def _http_get_json(url: str, params: dict[str, str]) -> _HTTPResult:
    """Perform a GET request and parse JSON, with a single retry on 429/5xx.

    Uses ``requests`` if importable; otherwise falls back to stdlib
    ``urllib.request``. Honors ``Retry-After`` for one retry.
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": _user_agent(),
    }

    # We will attempt at most twice: initial + one retry guided by Retry-After
    attempts = 2
    for attempt in range(attempts):
        _respect_rate_limit()
        try:
            # Try using requests if available
            try:
                import requests  # pyright: ignore[reportMissingModuleSource] - optional dependency

                resp = requests.get(url, params=params, headers=headers, timeout=(5.0, 15.0))
                status: int = int(resp.status_code)
                resp_headers: dict[str, str] = {str(k): str(v) for k, v in resp.headers.items()}
                if status == 429 or status >= 500:
                    retry_after = _parse_retry_after(resp_headers.get("Retry-After"))
                    if attempt < attempts - 1:
                        delay = max(1.0, min(10.0, retry_after or 1.0))
                        logger.warning(
                            "MusicBrainz rate-limited/server error (status=%s). Retrying in %.1fs.",
                            status,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    logger.warning(
                        "MusicBrainz rate-limited/server error (status=%s). Giving up.", status
                    )
                    return _HTTPResult(status=status, headers=resp_headers, data=None)

                # For other non-2xx statuses, warn and stop
                if status < 200 or status >= 300:
                    logger.warning("MusicBrainz HTTP error: status=%s", status)
                    return _HTTPResult(status=status, headers=resp_headers, data=None)

                try:
                    data = resp.json()
                except Exception as e:  # JSON decode errors vary across versions
                    logger.warning("MusicBrainz JSON parse error: %s", e)
                    return _HTTPResult(status=status, headers=resp_headers, data=None)

                return _HTTPResult(status=status, headers=resp_headers, data=data)

            except ModuleNotFoundError:
                # Fallback to urllib if requests is not available
                from urllib.parse import urlencode
                from urllib.request import Request, urlopen
                from urllib.error import HTTPError, URLError

                full_url = f"{url}?{urlencode(params)}"
                req = Request(full_url, method="GET", headers=headers)
                try:
                    with urlopen(req, timeout=15.0) as resp:  # noqa: S310 (trusted domain)
                        status = int(resp.getcode() or 0)
                        # Convert HTTPMessage to dict[str, str]
                        resp_headers_ul: dict[str, str] = {
                            str(k): str(v) for k, v in (resp.headers.items() if resp.headers else [])
                        }
                        raw = resp.read()
                except HTTPError as e:
                    status = int(e.code)
                    resp_headers_ul = {str(k): str(v) for k, v in (e.headers.items() if e.headers else [])}
                    if status == 429 or status >= 500:
                        retry_after = _parse_retry_after(resp_headers_ul.get("Retry-After"))
                        if attempt < attempts - 1:
                            delay = max(1.0, min(10.0, retry_after or 1.0))
                            logger.warning(
                                "MusicBrainz rate-limited/server error (status=%s). Retrying in %.1fs.",
                                status,
                                delay,
                            )
                            time.sleep(delay)
                            continue
                        logger.warning(
                            "MusicBrainz rate-limited/server error (status=%s). Giving up.", status
                        )
                        return _HTTPResult(status=status, headers=resp_headers_ul, data=None)
                    logger.warning("MusicBrainz HTTP error: status=%s", status)
                    return _HTTPResult(status=status, headers=resp_headers_ul, data=None)
                except URLError as e:  # pragma: no cover - network issue path
                    logger.warning("MusicBrainz request error: %s", e)
                    return _HTTPResult(status=0, headers={}, data=None)

                # Successful response with urllib
                try:
                    data = json.loads(raw.decode("utf-8"))
                except Exception as e:
                    logger.warning("MusicBrainz JSON parse error: %s", e)
                    return _HTTPResult(status=status, headers=resp_headers_ul, data=None)

                return _HTTPResult(status=status, headers=resp_headers_ul, data=data)

        except Exception as e:  # pragma: no cover - catch-all safeguard
            logger.warning("MusicBrainz unexpected error: %s", e)
            return _HTTPResult(status=0, headers={}, data=None)

    # Should not reach here due to returns above
    return _HTTPResult(status=0, headers={}, data=None)


# --- Domain helpers --------------------------------------------------------


def configure_romanization_cache(cache: _RomanizationCache | None) -> None:
    """Configure the cache used to persist romanized artist names."""

    global _romanization_cache
    _romanization_cache = cache


def _cache_romanized_name(original: str, romanized: str, *, source: str | None = None) -> None:
    if _romanization_cache is None:
        return
    try:
        if not romanized.strip():
            return
        _ = _romanization_cache.upsert_romanized_name(
            original,
            romanized.strip(),
            source=source,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to cache romanized name for '%s': %s", original, exc)

def _truthy(value: Any) -> bool:
    """Return True if the value is a truthy indicator (for 'primary')."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def _pick_best_artist(artists: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the most relevant artist from search results.

    Prefers the highest ``score`` if present; otherwise the first entry.
    """
    if not artists:
        return None
    try:
        return max(artists, key=lambda a: int(a.get("score", 0)))
    except Exception:
        return artists[0]


def _choose_romanized_from_aliases(aliases: list[dict[str, Any]] | None) -> str | None:
    """Select a romanized alias if available.

    Prefers alias with ``locale == 'ja-Latn'`` and ``primary == true``.
    Returns ``alias['sort-name']`` if present; otherwise ``alias['name']``.
    """
    if not aliases:
        return None
    for alias in aliases:
        if alias.get("locale") == "ja-Latn" and _truthy(alias.get("primary")):
            return alias.get("sort-name") or alias.get("name")
    return None


def fetch_romanized_name(name: str) -> str | None:
    """Fetch a romanized artist name from MusicBrainz.

    The function searches artists using WS2 and attempts to return a
    romanized name. The selection priority is:

    1. Alias where ``locale == 'ja-Latn'`` and ``primary == true``
    2. Artist ``sort-name``

    Args:
        name: Free-form artist name to query (used as ``artist:<name>``).

    Returns:
        The romanized artist name, or ``None`` if not determinable or upon
        HTTP/JSON errors.
    """
    trimmed = name.strip()
    if not trimmed:
        return None

    cached_value: str | None = None
    if _romanization_cache is not None:
        try:
            cached_value = _romanization_cache.get_romanized_name(trimmed)
        except Exception as exc:  # pragma: no cover - cache read failures logged only
            logger.warning("Failed to read romanization cache for '%s': %s", trimmed, exc)
    if cached_value:
        return cached_value

    q = f"artist:{trimmed}"

    result = _http_get_json(MB_BASE_URL, {"query": q, "fmt": "json"})
    data = result.data
    if data is None:
        return None

    artists = data.get("artists")
    if not isinstance(artists, list) or not artists:
        return None

    best = _pick_best_artist(artists)
    if best is None:
        return None

    romanized = _choose_romanized_from_aliases(best.get("aliases"))
    if romanized:
        _cache_romanized_name(trimmed, romanized, source="musicbrainz")
        return romanized

    # Fallback to sort-name
    sort_name = best.get("sort-name")
    if isinstance(sort_name, str) and sort_name.strip():
        sanitized = sort_name.strip()
        _cache_romanized_name(trimmed, sanitized, source="musicbrainz")
        return sanitized

    return None


def format_user_agent(app_name: str, app_version: str, contact: str) -> str:
    """Format a MusicBrainz-compliant User-Agent string.

    Args:
        app_name: Application name.
        app_version: Application version.
        contact: Contact URL or email. If empty, the parentheses part is omitted.

    Returns:
        Formatted User-Agent string like ``"app/1.0 (contact)"``.
    """
    if contact.strip():
        return f"{app_name}/{app_version} ({contact.strip()})"
    return f"{app_name}/{app_version}"


class MusicBrainzClient:
    """Lightweight MusicBrainz WS2 client.

    Currently provides only the ``fetch_romanized_name`` convenience method.
    The instance stores a preformatted User-Agent as recommended by
    MusicBrainz best practices.
    """

    def __init__(self, app_name: str, app_version: str, contact: str) -> None:
        self.user_agent: str = format_user_agent(app_name, app_version, contact)

    def fetch_romanized_name(self, name: str) -> str | None:
        """Instance variant that delegates to the module implementation."""
        return fetch_romanized_name(name)


# Prepare a default client using configured identity and expose its UA to
# the module-level HTTP helper.
_DEFAULT_CLIENT = MusicBrainzClient(MB_APP_NAME, MB_APP_VERSION, MB_CONTACT)
_client_ua = _DEFAULT_CLIENT.user_agent


__all__ = [
    "configure_romanization_cache",
    "fetch_romanized_name",
    "MusicBrainzClient",
    "format_user_agent",
]
