"""Where: src/omym/platform/musicbrainz/user_agent.py
What: Manage MusicBrainz-compliant User-Agent strings.
Why: Centralise etiquette logic shared by HTTP adapters and clients.
"""

from __future__ import annotations

import os

from omym.config.settings import MB_APP_NAME, MB_APP_VERSION, MB_CONTACT

_client_user_agent: str | None = None


def format_user_agent(app_name: str, app_version: str, contact: str) -> str:
    """Return ``App/Version (contact)`` when contact information is available."""

    stripped = contact.strip()
    if stripped:
        return f"{app_name}/{app_version} ({stripped})"
    return f"{app_name}/{app_version}"


def configure_client_user_agent(user_agent: str | None) -> None:
    """Record the user agent prepared by a MusicBrainzClient instance."""

    global _client_user_agent
    _client_user_agent = user_agent


def resolve_user_agent() -> str:
    """Provide the user agent that outbound HTTP calls should send."""

    if _client_user_agent:
        return _client_user_agent
    env = os.getenv("MUSICBRAINZ_USER_AGENT")
    if env:
        return env
    return format_user_agent(MB_APP_NAME, MB_APP_VERSION, MB_CONTACT)


__all__ = [
    "configure_client_user_agent",
    "format_user_agent",
    "resolve_user_agent",
]
