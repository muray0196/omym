"""Artist romanization helpers using MusicBrainz."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import langid
import pykakasi

from omym.config.settings import USE_MB_ROMANIZATION
from omym.platform.logging.logger import logger
from omym.platform.musicbrainz.client import fetch_romanized_name

from ..domain.track_metadata import TrackMetadata

ArtistFetcher = Callable[[str], str | None]
LanguageDetector = Callable[[str], str | None]
Transliterator = Callable[[str], str]

_TARGET_LANGS = {"ja", "zh"}
_KAKASI = pykakasi.Kakasi()


def _default_enabled() -> bool:
    """Return whether MusicBrainz romanization is enabled via settings."""
    return USE_MB_ROMANIZATION


def _default_fetcher(name: str) -> str | None:
    """Default fetcher delegating to the MusicBrainz client helper."""
    logger.info("Querying MusicBrainz for romanized name: '%s'", name)
    return fetch_romanized_name(name)


def _default_language_detector(text: str) -> str | None:
    """Detect language code for deciding whether to romanize via MusicBrainz."""

    try:
        lang, _ = langid.classify(text)
        return str(lang)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Language detection failed for '%s': %s", text, exc)
        return None


def _default_transliterator(text: str) -> str:
    """Fallback transliteration using pykakasi."""

    try:
        converted = _KAKASI.convert(text)
        romanized = "".join(item.get("hepburn", "") for item in converted).strip()
        return romanized or text
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Fallback transliteration failed for '%s': %s", text, exc)
        return text


@dataclass(slots=True)
class ArtistRomanizer:
    """Romanize artist names using MusicBrainz WS2.

    The class memoizes lookups within its lifecycle to avoid duplicated
    network calls and obey MusicBrainz rate limiting etiquette enforced by
    the shared client module.
    """

    enabled_supplier: Callable[[], bool] = field(default=_default_enabled)
    fetcher: ArtistFetcher = field(default=_default_fetcher)
    language_detector: LanguageDetector = field(default=_default_language_detector)
    transliterator: Transliterator = field(default=_default_transliterator)
    _cache: dict[str, str] = field(default_factory=dict, init=False)
    _last_fetch_source: str | None = field(default=None, init=False, repr=False)
    _last_fetch_original: str | None = field(default=None, init=False, repr=False)
    _last_fetch_value: str | None = field(default=None, init=False, repr=False)

    def record_fetch_context(
        self,
        *,
        source: str,
        original: str,
        value: str | None,
    ) -> None:
        """Record how the most recent fetch obtained its value."""

        self._last_fetch_source = source
        self._last_fetch_original = original
        self._last_fetch_value = value

    def _consume_fetch_context(self, original: str, value: str | None) -> str | None:
        if (
            self._last_fetch_original == original
            and self._last_fetch_value == value
            and self._last_fetch_source is not None
        ):
            source = self._last_fetch_source
            self._last_fetch_source = None
            self._last_fetch_original = None
            self._last_fetch_value = None
            return source
        self._last_fetch_source = None
        self._last_fetch_original = None
        self._last_fetch_value = None
        return None

    def romanize_name(self, name: str | None) -> str | None:
        """Return a romanized version of an artist name when available.

        Args:
            name: Raw artist name extracted from metadata.

        Returns:
            Romanized artist name if MusicBrainz returns one; otherwise the
            original name (including whitespace-only inputs).
        """
        if name is None:
            return None
        trimmed = name.strip()
        if not trimmed:
            return name
        if not self.enabled_supplier():
            return name

        if ", " in trimmed:
            parts = [part.strip() for part in trimmed.split(", ") if part.strip()]
            if not parts:
                return name
            romanized_parts = [self._romanize_single(part) for part in parts]
            return ", ".join(romanized_parts)

        return self._romanize_single(trimmed)

    def _romanize_single(self, text: str) -> str:
        cached = self._cache.get(text)
        if cached is not None:
            logger.debug("Using cached romanized name for '%s': %s", text, cached)
            return cached

        detected_lang = self.language_detector(text)
        if detected_lang not in _TARGET_LANGS:
            self._cache[text] = text
            return text

        try:
            romanized = self.fetcher(text)
        except Exception as exc:  # pragma: no cover - defensive logging only
            logger.warning("Failed to romanize artist '%s': %s", text, exc)
            romanized = None

        normalized = romanized.strip() if romanized else None
        if normalized:
            source = self._consume_fetch_context(text, romanized)
            if source == "cache":
                logger.info("Using cached MusicBrainz romanized '%s' -> '%s'", text, normalized)
            else:
                logger.info("MusicBrainz romanized '%s' -> '%s'", text, normalized)
            self._cache[text] = normalized
            return normalized

        fallback = self.transliterator(text).strip()
        if fallback:
            logger.info(
                "MusicBrainz fallback transliteration for '%s' -> '%s'",
                text,
                fallback,
            )
            self._cache[text] = fallback
            return fallback

        self._cache[text] = text
        return text

    def romanize_metadata(self, metadata: TrackMetadata | None) -> TrackMetadata | None:
        """Apply romanization to artist-related fields within metadata.

        Args:
            metadata: Mutable track metadata structure to update.

        Returns:
            The same metadata instance with artist fields optionally
            romanized. ``None`` is returned if ``metadata`` is ``None``.
        """
        if metadata is None:
            return None
        metadata.artist = self.romanize_name(metadata.artist)
        metadata.album_artist = self.romanize_name(metadata.album_artist)
        return metadata
