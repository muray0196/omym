"""Artist ID generation helpers.

Where: features/path/usecases/renamer/artist_id.py
What: Derive deterministic artist identifiers with transliteration and sanitization.
Why: Decouple ID heuristics from higher-level use cases for reuse and testing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, final

import langid
import pykakasi
from unidecode import unidecode

from omym.config.settings import ARTIST_ID_MAX_LENGTH
from omym.features.path.domain.sanitizer import Sanitizer
from omym.platform.logging import logger


@dataclass
class _WordToken:
    """Single character token with inclusion state."""

    char: str
    is_processed: bool
    included: bool = False


@dataclass
class _WordState:
    """Track per-word token selections during ID assembly."""

    tokens: list[_WordToken]
    next_unused_idx: int = 0

    @classmethod
    def from_processed(cls, processed: str, original: str) -> _WordState:
        """Create state from processed and original word variants."""

        if not processed and not original:
            return cls(tokens=[])

        tokens: list[_WordToken] = []
        processed_idx = 0

        for char in original:
            if processed_idx < len(processed) and char == processed[processed_idx]:
                tokens.append(_WordToken(char=char, is_processed=True))
                processed_idx += 1
            else:
                tokens.append(_WordToken(char=char, is_processed=False))

        return cls(tokens=tokens)

    def current_chars(self) -> str:
        """Return currently selected characters for concatenation."""

        return "".join(token.char for token in self.tokens if token.included)

    def current_length(self) -> int:
        """Number of currently selected characters."""

        return sum(1 for token in self.tokens if token.included)

    def processed_total(self) -> int:
        """Count processed tokens available for selection."""

        return sum(1 for token in self.tokens if token.is_processed)

    def include_processed_prefix(self, count: int) -> None:
        """Mark the first 'count' processed tokens as included."""

        remaining = count
        for token in self.tokens:
            if token.is_processed:
                token.included = remaining > 0
                if token.included:
                    remaining -= 1
                continue
            token.included = False

        self.next_unused_idx = 0

    def has_unused_tokens(self) -> bool:
        """Check if unused non-processed tokens remain."""

        return any(not token.included and not token.is_processed for token in self.tokens)

    def activate_next_token(self) -> bool:
        """Activate the next unused non-processed token in original order."""

        idx = self.next_unused_idx
        while idx < len(self.tokens):
            token = self.tokens[idx]
            if not token.included and not token.is_processed:
                token.included = True
                self.next_unused_idx = idx + 1
                return True
            idx += 1
        self.next_unused_idx = len(self.tokens)
        return False


@final
class ArtistIdGenerator:
    """Generate artist IDs."""

    KEEP_CHARS: ClassVar[re.Pattern[str]] = re.compile(r"[^A-Z0-9-]")
    VOWELS: ClassVar[re.Pattern[str]] = re.compile(r"[AEIOU]")
    ID_LENGTH: ClassVar[int] = ARTIST_ID_MAX_LENGTH
    DEFAULT_ID: ClassVar[str] = "NOART"
    FALLBACK_ID: ClassVar[str] = "X" * ARTIST_ID_MAX_LENGTH
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
    def _build_balanced_id(
        cls,
        processed_results: list[tuple[str, str]],
        target_length: int,
    ) -> str:
        """Assemble an ID respecting per-word order and balance."""

        states = [
            _WordState.from_processed(processed or "", original or "")
            for processed, original in processed_results
            if (processed or original)
        ]

        if not states:
            return ""

        cls._select_processed_tokens(states, target_length)
        cls._expand_states(states, target_length)

        return "".join(state.current_chars() for state in states)

    @staticmethod
    def _select_processed_tokens(states: list[_WordState], target_length: int) -> None:
        """Allocate processed characters per word using round-robin selection."""

        processed_totals = [state.processed_total() for state in states]
        total_processed = sum(processed_totals)

        if total_processed == 0:
            return

        if total_processed <= target_length:
            for state, count in zip(states, processed_totals):
                state.include_processed_prefix(count)
            return

        allocations = [0] * len(states)
        remaining = target_length
        active_indices = [idx for idx, count in enumerate(processed_totals) if count > 0]
        position = 0

        while remaining > 0 and active_indices:
            current_idx = active_indices[position]
            count = processed_totals[current_idx]

            if allocations[current_idx] < count:
                allocations[current_idx] += 1
                remaining -= 1

            if allocations[current_idx] >= count:
                _ = active_indices.pop(position)
                if not active_indices:
                    break
                if position >= len(active_indices):
                    position = 0
            else:
                position = (position + 1) % len(active_indices)

        for state, count in zip(states, allocations):
            state.include_processed_prefix(count)

    @staticmethod
    def _expand_states(states: list[_WordState], target_length: int) -> None:
        """Expand IDs by re-introducing original characters."""

        total_length = sum(state.current_length() for state in states)
        if total_length >= target_length:
            return

        active_indices = [idx for idx, state in enumerate(states) if state.has_unused_tokens()]
        position = 0

        while active_indices and total_length < target_length:
            current_idx = active_indices[position]
            state = states[current_idx]
            if state.activate_next_token():
                total_length += 1

            if not state.has_unused_tokens():
                _ = active_indices.pop(position)
                if position >= len(active_indices):
                    position = 0
            else:
                position = (position + 1) % len(active_indices)

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
    def _split_artists(cls, artist_name: str) -> list[str]:
        """Split raw artist string into individual artists by comma."""

        parts = [part.strip() for part in artist_name.split(",")]
        return [part for part in parts if part]

    @classmethod
    def _normalize_artist(cls, artist: str) -> str:
        """Transliterate, sanitize, and uppercase a single artist name."""

        name = artist

        try:
            lang, _ = langid.classify(name)
            if lang in ["ja", "zh"]:
                name = cls._transliterate_japanese(name)
            else:
                name = unidecode(name)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Language detection/transliteration failed for '%s': %s",
                artist,
                exc,
            )
            name = unidecode(artist)

        sanitized = Sanitizer.sanitize_artist_name(name).upper()
        return sanitized

    @classmethod
    def _prepare_artist_segments(
        cls,
        artist: str,
    ) -> tuple[list[tuple[str, str]], str]:
        """Return per-segment processed pairs alongside normalized text."""

        normalized = cls._normalize_artist(artist)
        if not normalized:
            return [], ""

        words = [word for word in normalized.split("-") if word]
        if not words:
            return [], normalized

        segments = [cls._process_word(word) for word in words]
        return segments, normalized

    @classmethod
    def _generate_single_artist_id(
        cls,
        segments: list[tuple[str, str]],
        normalized: str,
        target_length: int,
    ) -> str:
        """Generate an ID for a single artist up to the requested length."""

        if target_length <= 0:
            return ""

        if not normalized:
            return cls.FALLBACK_ID[: target_length]

        if len(normalized) <= target_length and "-" not in normalized:
            return normalized[:target_length]

        if not segments:
            return normalized[:target_length]

        balanced_id = cls._build_balanced_id(segments, target_length)
        if balanced_id:
            return balanced_id[:target_length]

        fallback = "".join(original for _, original in segments if original)
        if fallback:
            return fallback[:target_length]

        return cls.FALLBACK_ID[: target_length]

    @staticmethod
    def _artist_token_capacity(
        segments: list[tuple[str, str]],
        normalized: str,
    ) -> int:
        """Estimate the maximum usable characters for a single artist."""

        capacity = sum(len(original or "") for _, original in segments if original)
        if capacity <= 0 and normalized:
            return len(normalized)
        return capacity

    @staticmethod
    def _distribute_artist_shares(
        capacities: list[int],
        target_length: int,
    ) -> list[int]:
        """Allocate per-artist character counts via round-robin rotation."""

        shares = [0] * len(capacities)
        active = [idx for idx, capacity in enumerate(capacities) if capacity > 0]
        if not active or target_length <= 0:
            return shares

        remaining = target_length
        position = 0

        while remaining > 0 and active:
            current_idx = active[position]
            shares[current_idx] += 1
            remaining -= 1

            if shares[current_idx] >= capacities[current_idx]:
                _ = active.pop(position)
                if not active:
                    break
                if position >= len(active):
                    position = 0
                continue

            position = (position + 1) % len(active)

        return shares

    @classmethod
    def _build_multi_artist_id(
        cls,
        artist_entries: list[tuple[list[tuple[str, str]], str]],
        target_length: int,
    ) -> str:
        """Generate a multi-artist ID using per-artist round-robin slices."""

        if not artist_entries or target_length <= 0:
            return ""

        capacities = [
            cls._artist_token_capacity(segments, normalized)
            for segments, normalized in artist_entries
        ]

        shares = cls._distribute_artist_shares(capacities, target_length)

        parts: list[str] = []
        for (segments, normalized), share in zip(artist_entries, shares):
            if share <= 0:
                parts.append("")
                continue

            artist_fragment = cls._generate_single_artist_id(
                segments,
                normalized,
                share,
            )

            if artist_fragment:
                parts.append(artist_fragment)
                continue

            sanitized = (normalized or "")[:share]
            if sanitized:
                parts.append(sanitized)
                continue

            fallback = "".join(original for _, original in segments if original)
            parts.append(fallback[:share])

        combined = "".join(parts)
        return combined[:target_length]

    @classmethod
    def generate(cls, artist_name: str | None) -> str:
        """Generate an artist ID up to the configured maximum length."""

        try:
            if not artist_name or not artist_name.strip():
                return cls.DEFAULT_ID

            artists = cls._split_artists(artist_name)

            if len(artists) <= 1:
                target = artist_name.strip()
                segments, normalized = cls._prepare_artist_segments(target)
                return cls._generate_single_artist_id(segments, normalized, cls.ID_LENGTH)

            artist_entries: list[tuple[list[tuple[str, str]], str]] = []
            normalized_parts: list[str] = []
            for artist in artists:
                segments, normalized = cls._prepare_artist_segments(artist)
                if segments or normalized:
                    artist_entries.append((segments, normalized))
                if normalized:
                    normalized_parts.append(normalized)

            multi_id = cls._build_multi_artist_id(artist_entries, cls.ID_LENGTH)
            if multi_id:
                return multi_id

            if normalized_parts:
                fallback_multi = "".join(normalized_parts)
                if fallback_multi:
                    return fallback_multi[: cls.ID_LENGTH]

            return cls.FALLBACK_ID[: cls.ID_LENGTH]

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to generate artist ID for '%s': %s", artist_name, exc)
            return cls.DEFAULT_ID


__all__ = ["ArtistIdGenerator"]
