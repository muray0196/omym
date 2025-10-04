"""Summary: Tests for the MusicBrainz romanization adapter.
Why: Verify delegation to platform-level MusicBrainz helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from omym.features.metadata.adapters import MusicBrainzRomanizationAdapter


def test_configure_cache_delegates_to_platform(mocker: MockerFixture) -> None:
    """Ensure cache configuration forwards to the platform helper."""

    adapter = MusicBrainzRomanizationAdapter()
    cache = MagicMock()
    configure = mocker.patch(
        "omym.features.metadata.adapters.romanization_adapter.configure_romanization_cache"
    )

    adapter.configure_cache(cache)

    configure.assert_called_once_with(cache)


def test_fetch_and_save_delegate_to_platform(mocker: MockerFixture) -> None:
    """Fetch and cache calls must reuse the platform wiring."""

    adapter = MusicBrainzRomanizationAdapter()
    fetch = mocker.patch(
        "omym.features.metadata.adapters.romanization_adapter.fetch_romanized_name",
        return_value="Utada Hikaru",
    )
    saver = mocker.patch(
        "omym.features.metadata.adapters.romanization_adapter.save_cached_name"
    )

    result = adapter.fetch_romanized_name("宇多田ヒカル")
    adapter.save_cached_name("宇多田ヒカル", "Utada Hikaru", source="musicbrainz")

    assert result == "Utada Hikaru"
    fetch.assert_called_once_with("宇多田ヒカル")
    saver.assert_called_once_with("宇多田ヒカル", "Utada Hikaru", source="musicbrainz")
