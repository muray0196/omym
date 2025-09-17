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

        romanizer = ArtistRomanizer(
            enabled_supplier=lambda: True,
            fetcher=fetcher,
            language_detector=lambda _: "ja",
            transliterator=lambda _: "fallback",
        )

        result = romanizer.romanize_name(" 宇多田ヒカル ")

        assert result == "Hikaru Utada"
        assert calls == ["宇多田ヒカル"]

    def test_romanize_name_disabled_returns_original(self) -> None:
        """Skip MusicBrainz requests when feature flag is disabled."""

        romanizer = ArtistRomanizer(
            enabled_supplier=lambda: False,
            fetcher=lambda _: "ignored",
            language_detector=lambda _: "ja",
            transliterator=lambda _: "fallback",
        )

        result = romanizer.romanize_name("宇多田ヒカル")

        assert result == "宇多田ヒカル"

    def test_romanize_metadata_updates_artist_fields(self) -> None:
        """Apply romanization to artist and album artist fields."""

        romanizer = ArtistRomanizer(
            enabled_supplier=lambda: True,
            fetcher=lambda _: "Hikaru Utada",
            language_detector=lambda _: "ja",
            transliterator=lambda _: "fallback",
        )
        metadata = TrackMetadata(artist="宇多田ヒカル", album_artist="宇多田ヒカル")

        updated = romanizer.romanize_metadata(metadata)

        assert updated is metadata
        assert metadata.artist == "Hikaru Utada"
        assert metadata.album_artist == "Hikaru Utada"

    def test_fallback_transliterator_used_when_fetcher_returns_none(self) -> None:
        romanizer = ArtistRomanizer(
            enabled_supplier=lambda: True,
            fetcher=lambda _: None,
            language_detector=lambda _: "ja",
            transliterator=lambda _: "Fallback",
        )

        result = romanizer.romanize_name("宇多田ヒカル")

        assert result == "Fallback"

    def test_english_names_bypass_musicbrainz(self) -> None:
        calls: list[str] = []

        def fetcher(_: str) -> str | None:
            calls.append("called")
            return "Should not happen"

        romanizer = ArtistRomanizer(
            enabled_supplier=lambda: True,
            fetcher=fetcher,
            language_detector=lambda _: "en",
            transliterator=lambda _: "fallback",
        )

        result = romanizer.romanize_name("Hikaru Utada")

        assert result == "Hikaru Utada"
        assert calls == []

    def test_multiple_artists_processed_individually(self) -> None:
        calls: list[str] = []

        def fetcher(name: str) -> str | None:
            calls.append(name)
            return f"R-{name}"

        romanizer = ArtistRomanizer(
            enabled_supplier=lambda: True,
            fetcher=fetcher,
            language_detector=lambda _: "ja",
            transliterator=lambda text: f"T-{text}",
        )

        result = romanizer.romanize_name("宇多田ヒカル, 米津玄師")

        assert result == "R-宇多田ヒカル, R-米津玄師"
        assert calls == ["宇多田ヒカル", "米津玄師"]
