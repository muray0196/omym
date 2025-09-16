from __future__ import annotations

from omym.domain.metadata.artist_romanizer import ArtistRomanizer
from omym.domain.metadata.track_metadata import TrackMetadata


class TestArtistRomanizer:
    """Unit tests for `ArtistRomanizer`."""

    def test_romanize_name_enabled_fetcher_used(self) -> None:
        """Fetch romanized value when feature flag is enabled."""

        calls: list[str] = []

        def fetcher(name: str) -> str | None:
            calls.append(name)
            return "Hikaru Utada"

        romanizer = ArtistRomanizer(enabled_supplier=lambda: True, fetcher=fetcher)

        result = romanizer.romanize_name(" 宇多田ヒカル ")

        assert result == "Hikaru Utada"
        assert calls == ["宇多田ヒカル"]

    def test_romanize_name_disabled_returns_original(self) -> None:
        """Skip MusicBrainz requests when feature flag is disabled."""

        romanizer = ArtistRomanizer(enabled_supplier=lambda: False, fetcher=lambda _: "ignored")

        result = romanizer.romanize_name("宇多田ヒカル")

        assert result == "宇多田ヒカル"

    def test_romanize_metadata_updates_artist_fields(self) -> None:
        """Apply romanization to artist and album artist fields."""

        romanizer = ArtistRomanizer(enabled_supplier=lambda: True, fetcher=lambda _: "Hikaru Utada")
        metadata = TrackMetadata(artist="宇多田ヒカル", album_artist="宇多田ヒカル")

        updated = romanizer.romanize_metadata(metadata)

        assert updated is metadata
        assert metadata.artist == "Hikaru Utada"
        assert metadata.album_artist == "Hikaru Utada"
