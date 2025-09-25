"""Artist ID generation helpers.

Where: features/path/usecases/renamer/artist_id.py
What: Derive deterministic artist identifiers with transliteration and sanitization.
Why: Decouple ID heuristics from higher-level use cases for reuse and testing.
"""

from __future__ import annotations

import re
from typing import ClassVar, final

import langid
import pykakasi
from unidecode import unidecode

from omym.features.path.domain.sanitizer import Sanitizer
from omym.platform.logging import logger


@final
class ArtistIdGenerator:
    """Generate artist IDs."""

    KEEP_CHARS: ClassVar[re.Pattern[str]] = re.compile(r"[^A-Z0-9-]")
    VOWELS: ClassVar[re.Pattern[str]] = re.compile(r"[AEIOU]")
    ID_LENGTH: ClassVar[int] = 5
    DEFAULT_ID: ClassVar[str] = "NOART"
    _kakasi: ClassVar = pykakasi.Kakasi()

    @classmethod
    def _process_word(cls, word: str) -> tuple[str, str]:
        """Process a single word by removing vowels after the first character."""

        if not word:
            return "", ""

        first_char = word[0]

        if len(word) > 1:
            rest = word[1:]
            rest = cls.VOWELS.sub("", rest)
            processed = first_char + rest
        else:
            processed = first_char

        return processed, word

    @classmethod
    def _transliterate_japanese(cls, text: str) -> str:
        """Transliterate Japanese text to Latin script using pykakasi."""

        try:
            result = cls._kakasi.convert(text)
            return "".join(item["hepburn"] for item in result).upper()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Japanese transliteration failed for '%s': %s", text, exc)
            return text

    @classmethod
    def generate(cls, artist_name: str | None) -> str:
        """Generate an artist ID (up to 5 characters) from an artist name."""

        try:
            if not artist_name or not artist_name.strip():
                return cls.DEFAULT_ID

            name = artist_name
            if ", " in artist_name:
                parts = [part.strip() for part in artist_name.split(", ") if part.strip()]
                if parts:
                    name = "".join(parts)

            try:
                lang, _ = langid.classify(name)
                if lang in ["ja", "zh"]:
                    name = cls._transliterate_japanese(name)
                else:
                    name = unidecode(name)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Language detection/transliteration failed for '%s': %s",
                    artist_name,
                    exc,
                )
                name = unidecode(artist_name)

            name = Sanitizer.sanitize_artist_name(name).upper()
            if not name:
                return "XXXXX"

            words = name.split("-")
            processed_results: list[tuple[str, str]] = [cls._process_word(word) for word in words]

            processed_words = [result[0] for result in processed_results]
            processed_id = "".join(processed_words)

            if len(processed_id) < cls.ID_LENGTH:
                name = "".join(result[1] for result in processed_results)
            else:
                name = processed_id

            if len(name) > cls.ID_LENGTH:
                return name[: cls.ID_LENGTH]
            return name

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to generate artist ID for '%s': %s", artist_name, exc)
            return cls.DEFAULT_ID


__all__ = ["ArtistIdGenerator"]
