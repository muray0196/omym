from __future__ import annotations

from pathlib import Path

import textwrap

import pytest

from omym.config.artist_name_preferences import (
    ArtistNamePreferenceRepository,
    ArtistNamePreferenceParseError,
    ArtistNamePreferenceValidationError,
    load_artist_name_preferences,
)


class TestArtistNamePreferencesLoader:
    """Unit tests for the TOML-based artist name preference loader."""

    def test_template_created_when_file_missing(self, tmp_path: Path) -> None:
        """Missing configuration produces a template and an empty store."""

        destination = tmp_path / "artist_name_preferences.toml"

        repository = load_artist_name_preferences(path=destination)

        assert destination.exists()
        template_text = destination.read_text(encoding="utf-8")
        assert "[preferences]" in template_text
        assert "宇多田ヒカル" not in template_text
        assert isinstance(repository, ArtistNamePreferenceRepository)
        assert repository.store.is_empty()

    def test_loads_overrides_and_resolves(self, tmp_path: Path) -> None:
        """Parse TOML preferences and resolve case-insensitive matches."""

        config_path = tmp_path / "artist_name_preferences.toml"
        _ = config_path.write_text(
            textwrap.dedent(
                """
                metadata_version = 2

                [defaults]
                locale = "en_GB"

                [preferences]
                "宇多田ヒカル" = "Utada Hikaru"
                perfume = "Perfume"
                "米津玄師" = "Kenshi Yonezu"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        repository = load_artist_name_preferences(path=config_path)

        assert repository.store.metadata_version == 2
        assert repository.resolve("宇多田ヒカル") == "Utada Hikaru"
        assert repository.resolve("Perfume") == "Perfume"
        assert repository.resolve("perfume") == "Perfume"
        assert repository.resolve("米津玄師") == "Kenshi Yonezu"
        # Blank entries should not override the original name.
        assert repository.resolve("LiSA") is None
        assert repository.store.defaults.get("locale") == "en_GB"

        repository.ensure_placeholder("初星学園")
        repository.ensure_placeholder("宇多田ヒカル")
        preferences = repository.snapshot()
        assert "初星学園" in preferences
        persisted = config_path.read_text(encoding="utf-8")
        assert '"初星学園" = ""' in persisted
        assert "Monogatari Series" not in persisted

    def test_duplicate_keys_raise_validation_error(self, tmp_path: Path) -> None:
        """Reject preferences whose keys collide after case normalisation."""

        config_path = tmp_path / "artist_name_preferences.toml"
        _ = config_path.write_text(
            textwrap.dedent(
                """
                [preferences]
                Perfume = "Perfume"
                perfume = "Duplicate"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ArtistNamePreferenceValidationError):
            _ = load_artist_name_preferences(path=config_path)

    def test_invalid_toml_raises_parse_error(self, tmp_path: Path) -> None:
        """Surface parse errors when TOML cannot be decoded."""

        config_path = tmp_path / "artist_name_preferences.toml"
        _ = config_path.write_text("not = [valid", encoding="utf-8")

        with pytest.raises(ArtistNamePreferenceParseError):
            _ = load_artist_name_preferences(path=config_path)

    def test_invalid_structure_raises_validation_error(self, tmp_path: Path) -> None:
        """Reject documents with non-table defaults/preferences sections."""

        config_path = tmp_path / "artist_name_preferences.toml"
        _ = config_path.write_text(
            textwrap.dedent(
                """
                defaults = "not-a-table"
                [preferences]
                "宇多田ヒカル" = "Utada Hikaru"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ArtistNamePreferenceValidationError):
            _ = load_artist_name_preferences(path=config_path)
