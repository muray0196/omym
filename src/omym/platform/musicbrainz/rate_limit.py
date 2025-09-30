"""Where: src/omym/platform/musicbrainz/rate_limit.py
What: Thread-safe throttle enforcing MusicBrainz WS2 request spacing.
Why: MusicBrainz asks clients to limit traffic to roughly 1 request per second.
"""

from __future__ import annotations

import threading
import time
from typing import Final


class RateLimiter:
    """Provide a minimal monotonic sleep guard for outgoing requests."""

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval: float = min_interval_seconds
        self._lock: Final[threading.Lock] = threading.Lock()
        self._last_start: float = 0.0

    def respect(self) -> None:
        """Delay the caller until the minimum spacing constraint is met."""

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_start
            wait = self._min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_start = time.monotonic()


_DEFAULT_MIN_INTERVAL: Final[float] = 1.0
_DEFAULT_RATE_LIMITER: Final[RateLimiter] = RateLimiter(_DEFAULT_MIN_INTERVAL)


def respect_rate_limit() -> None:
    """Block until the shared rate limiter allows another request."""

    _DEFAULT_RATE_LIMITER.respect()


__all__ = [
    "RateLimiter",
    "respect_rate_limit",
]
