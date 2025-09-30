"""Where: src/omym/platform/musicbrainz/http_client.py
What: HTTP adapter with retry and fallback logic for MusicBrainz WS2 requests.
Why: Decouple network concerns from romanization parsing and caching.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Protocol, cast

from omym.platform.logging import logger

from .rate_limit import respect_rate_limit
from .user_agent import resolve_user_agent


@dataclass(slots=True)
class HTTPResult:
    """Represent an HTTP response payload relevant to the MusicBrainz client."""

    status: int
    headers: dict[str, str]
    data: dict[str, Any] | None


class HTTPClient(Protocol):
    """Protocol for HTTP clients able to fetch JSON payloads."""

    def get_json(self, url: str, params: dict[str, str]) -> HTTPResult:
        ...


class MusicBrainzHTTPClient:
    """Perform GET requests with retries and a ``requests`` fallback."""

    _MAX_ATTEMPTS: int = 2

    def get_json(self, url: str, params: dict[str, str]) -> HTTPResult:
        headers = {
            "Accept": "application/json",
            "User-Agent": resolve_user_agent(),
        }

        for attempt in range(self._MAX_ATTEMPTS):
            respect_rate_limit()
            try:
                result = self._attempt_with_requests(url, params, headers)
            except ModuleNotFoundError:
                result = self._attempt_with_urllib(url, params, headers)
            except Exception as exc:  # pragma: no cover - defensive logging path
                logger.warning("MusicBrainz unexpected error: %s", exc)
                return HTTPResult(status=0, headers={}, data=None)

            if self._should_retry(result.status):
                if attempt < self._MAX_ATTEMPTS - 1:
                    delay = self._retry_delay(result.headers)
                    logger.warning(
                        "MusicBrainz rate-limited/server error (status=%s). Retrying in %.1fs.",
                        result.status,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                logger.warning(
                    "MusicBrainz rate-limited/server error (status=%s). Giving up.",
                    result.status,
                )
                return HTTPResult(status=result.status, headers=result.headers, data=None)

            if result.status and (result.status < 200 or result.status >= 300):
                logger.warning("MusicBrainz HTTP error: status=%s", result.status)
                return HTTPResult(status=result.status, headers=result.headers, data=None)

            return result

        return HTTPResult(status=0, headers={}, data=None)

    def _attempt_with_requests(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> HTTPResult:
        import requests  # pyright: ignore[reportMissingModuleSource] - optional dependency

        response = requests.get(url, params=params, headers=headers, timeout=(5.0, 15.0))
        status = int(response.status_code)
        header_items = cast(Iterable[tuple[str, str]], response.headers.items())
        response_headers = {str(key): str(value) for key, value in header_items}

        if not 200 <= status < 300:
            return HTTPResult(status=status, headers=response_headers, data=None)

        try:
            data = response.json()
        except Exception as exc:
            logger.warning("MusicBrainz JSON parse error: %s", exc)
            return HTTPResult(status=status, headers=response_headers, data=None)

        return HTTPResult(status=status, headers=response_headers, data=data)

    def _attempt_with_urllib(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> HTTPResult:
        from urllib.error import HTTPError, URLError
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        full_url = f"{url}?{urlencode(params)}"
        request = Request(full_url, method="GET", headers=headers)
        try:
            with urlopen(request, timeout=15.0) as response:  # noqa: S310 (trusted domain)
                status = int(response.getcode() or 0)
                header_items = cast(
                    Iterable[tuple[str, str]],
                    response.headers.items() if response.headers else [],
                )
                response_headers = {str(key): str(value) for key, value in header_items}
                raw = response.read()
        except HTTPError as exc:
            status = int(exc.code)
            header_items = cast(
                Iterable[tuple[str, str]],
                exc.headers.items() if exc.headers else [],
            )
            response_headers = {str(key): str(value) for key, value in header_items}
            if not 200 <= status < 300:
                return HTTPResult(status=status, headers=response_headers, data=None)
            raw = exc.read()
        except URLError as exc:  # pragma: no cover - network issue path
            logger.warning("MusicBrainz request error: %s", exc)
            return HTTPResult(status=0, headers={}, data=None)

        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            logger.warning("MusicBrainz JSON parse error: %s", exc)
            return HTTPResult(status=status, headers=response_headers, data=None)

        return HTTPResult(status=status, headers=response_headers, data=data)

    @staticmethod
    def _should_retry(status: int) -> bool:
        return status == 429 or status >= 500

    @staticmethod
    def _retry_delay(headers: dict[str, str]) -> float:
        retry_after = _parse_retry_after(headers.get("Retry-After"))
        return max(1.0, min(10.0, retry_after or 1.0))


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    stripped = value.strip()
    if stripped.isdigit():
        return float(int(stripped))
    try:
        dt = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if dt is None:  # pragma: no cover - defensive for older stdlib behaviour  # pyright: ignore[reportUnnecessaryComparison]
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (dt - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delta)


DEFAULT_HTTP_CLIENT = MusicBrainzHTTPClient()


__all__ = [
    "DEFAULT_HTTP_CLIENT",
    "HTTPClient",
    "HTTPResult",
    "MusicBrainzHTTPClient",
]
