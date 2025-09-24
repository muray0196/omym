from __future__ import annotations

from omym.platform.musicbrainz.client import MusicBrainzClient, format_user_agent


def test_format_user_agent_with_contact() -> None:
    assert format_user_agent("app", "1.2.3", "mailto:test@example.com") == "app/1.2.3 (mailto:test@example.com)"


def test_format_user_agent_without_contact() -> None:
    assert format_user_agent("app", "1.2.3", "") == "app/1.2.3"


def test_client_sets_user_agent() -> None:
    client = MusicBrainzClient("myapp", "0.2.0", "https://example.com/contact")
    assert client.user_agent == "myapp/0.2.0 (https://example.com/contact)"
