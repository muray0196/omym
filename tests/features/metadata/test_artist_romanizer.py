"""Summary: Tests for ArtistRomanizer behaviour.
Why: Validate caching, fallback, and MusicBrainz port interactions."""

from __future__ import annotations

from omym.features.metadata import ArtistRomanizer
from omym.features.metadata.usecases.ports import RomanizationPort
from omym.shared import TrackMetadata


class _StubRomanizationPort(RomanizationPort):
    """In-memory stub capturing cache persistence calls."""

    def __init__(self) -> None:
        self.configured_with: object | None = None
        self.saved: list[tuple[str, str, str | None]] = []

    def configure_cache(self, cache: object | None) -> None:  # pragma: no cover - trivial
        self.configured_with = cache

    def fetch_romanized_name(self, artist_name: str) -> str | None:  # pragma: no cover - default unused
        del artist_name
        return None

    def save_cached_name(
        self,
        original: str,
        romanized: str,
        *,
        source: str | None = None,
    ) -> None:
        self.saved.append((original, romanized, source))


class TestArtistRomanizer:
    """Unit tests for `ArtistRomanizer`."""

    def test_romanize_name_enabled_fetcher_used(self) -> None:
        """Fetch romanized value when feature flag is enabled."""

        calls: list[str] = []

        def fetcher(name: str) -> str | None:
            calls.append(name)
            return "Hikaru Utada"

        romanizer = ArtistRomanizer(
            romanization_port=_StubRomanizationPort(),
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
            romanization_port=_StubRomanizationPort(),
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
            romanization_port=_StubRomanizationPort(),
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
        port = _StubRomanizationPort()

        romanizer = ArtistRomanizer(
            romanization_port=port,
            enabled_supplier=lambda: True,
            fetcher=lambda _: None,
            language_detector=lambda _: "ja",
            transliterator=lambda _: "Fallback",
        )

        result = romanizer.romanize_name("宇多田ヒカル")

        assert result == "Fallback"
        assert port.saved == [("宇多田ヒカル", "Fallback", "transliteration")]

    def test_musicbrainz_non_latin_value_triggers_transliterator(self) -> None:
        romanizer = ArtistRomanizer(
            romanization_port=_StubRomanizationPort(),
            enabled_supplier=lambda: True,
            fetcher=lambda _: "雀が原中学卓球部",
            language_detector=lambda _: "ja",
            transliterator=lambda _: "Suzumegarasu Chugaku Takkyubu",
        )

        first_result = romanizer.romanize_name("雀が原中学卓球部")

        assert first_result == "Suzumegarasu Chugaku Takkyubu"
        assert romanizer.consume_last_result_source() == "transliteration"

        second_result = romanizer.romanize_name("雀が原中学卓球部")

        assert second_result == "Suzumegarasu Chugaku Takkyubu"
        assert romanizer.consume_last_result_source() == "cache"

    def test_english_names_bypass_musicbrainz(self) -> None:
        calls: list[str] = []

        def fetcher(_: str) -> str | None:
            calls.append("called")
            return "Should not happen"

        romanizer = ArtistRomanizer(
            romanization_port=_StubRomanizationPort(),
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

        romanized_values = {
            "宇多田ヒカル": "Utada Hikaru",
            "米津玄師": "Yonezu Kenshi",
        }

        def fetcher(name: str) -> str | None:
            calls.append(name)
            return romanized_values[name]

        romanizer = ArtistRomanizer(
            romanization_port=_StubRomanizationPort(),
            enabled_supplier=lambda: True,
            fetcher=fetcher,
            language_detector=lambda _: "ja",
            transliterator=lambda text: f"T-{text}",
        )

        result = romanizer.romanize_name("宇多田ヒカル, 米津玄師")

        assert result == "Utada Hikaru, Yonezu Kenshi"
        assert calls == ["宇多田ヒカル", "米津玄師"]

    def test_musicbrainz_formatted_name_not_re_romanized(self) -> None:
        """Skip re-romanization for names already formatted by MusicBrainz."""

        calls: list[str] = []

        def fetcher(name: str) -> str | None:
            calls.append(name)
            assert name == "佐藤貴文"
            return "Satō, Takafumi"

        def detector(text: str) -> str | None:
            return "ja" if text == "佐藤貴文" else "en"

        romanizer = ArtistRomanizer(
            romanization_port=_StubRomanizationPort(),
            enabled_supplier=lambda: True,
            fetcher=fetcher,
            language_detector=detector,
            transliterator=lambda _: "fallback",
        )

        first_pass = romanizer.romanize_name("佐藤貴文")
        assert first_pass == "Satō, Takafumi"

        second_pass = romanizer.romanize_name(first_pass)

        assert second_pass == "Satō, Takafumi"
        assert calls == ["佐藤貴文"]
