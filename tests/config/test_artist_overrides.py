from __future__ import annotations

from pathlib import Path

import textwrap

import pytest

from omym.config.artist_overrides import (
    ArtistOverrideRepository,
    ArtistOverridesParseError,
    ArtistOverridesValidationError,
    load_artist_overrides,
)


class TestArtistOverridesLoader:
    """Unit tests for the TOML-based artist override loader."""

    def test_template_created_when_file_missing(self, tmp_path: Path) -> None:
        """Missing configuration produces a template and an empty store."""

        destination = tmp_path / "artist_overrides.toml"

        repository = load_artist_overrides(path=destination)

        assert destination.exists()
        template_text = destination.read_text(encoding="utf-8")
        assert "[overrides]" in template_text
        assert "宇多田ヒカル" not in template_text
        assert isinstance(repository, ArtistOverrideRepository)
        assert repository.store.is_empty()

    def test_loads_overrides_and_resolves(self, tmp_path: Path) -> None:
        """Parse TOML overrides and resolve case-insensitive matches."""

        config_path = tmp_path / "artist_overrides.toml"
        _ = config_path.write_text(
            textwrap.dedent(
                """
                metadata_version = 2

                [defaults]
                locale = "en_GB"

                [overrides]
                "宇多田ヒカル" = "Utada Hikaru"
                perfume = "Perfume"
                "米津玄師" = "Kenshi Yonezu"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        repository = load_artist_overrides(path=config_path)

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
        overrides = repository.snapshot()
        assert "初星学園" in overrides
        persisted = config_path.read_text(encoding="utf-8")
        assert '"初星学園" = ""' in persisted
        assert "Monogatari Series" not in persisted

    def test_duplicate_keys_raise_validation_error(self, tmp_path: Path) -> None:
        """Reject overrides whose keys collide after case normalisation."""

        config_path = tmp_path / "artist_overrides.toml"
        _ = config_path.write_text(
            textwrap.dedent(
                """
                [overrides]
                Perfume = "Perfume"
                perfume = "Duplicate"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ArtistOverridesValidationError):
            _ = load_artist_overrides(path=config_path)

    def test_invalid_toml_raises_parse_error(self, tmp_path: Path) -> None:
        """Surface parse errors when TOML cannot be decoded."""

        config_path = tmp_path / "artist_overrides.toml"
        _ = config_path.write_text("not = [valid", encoding="utf-8")

        with pytest.raises(ArtistOverridesParseError):
            _ = load_artist_overrides(path=config_path)

    def test_invalid_structure_raises_validation_error(self, tmp_path: Path) -> None:
        """Reject documents with non-table defaults/overrides sections."""

        config_path = tmp_path / "artist_overrides.toml"
        _ = config_path.write_text(
            textwrap.dedent(
                """
                defaults = "not-a-table"
                [overrides]
                "宇多田ヒカル" = "Utada Hikaru"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ArtistOverridesValidationError):
            _ = load_artist_overrides(path=config_path)
