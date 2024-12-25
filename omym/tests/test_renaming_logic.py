"""Test renaming logic functionality."""

import pytest
from pathlib import Path
from unidecode import unidecode
import langid
import pykakasi

from omym.core.renaming_logic import (
    ArtistIdGenerator,
    CachedArtistIdGenerator,
    DirectoryGenerator,
)
from omym.core.metadata import TrackMetadata
from omym.db.dao_artist_cache import ArtistCacheDAO
from omym.db.db_manager import DatabaseManager


class TestArtistIdGenerator:
    """Test cases for ArtistIdGenerator class."""

    def test_process_word(self) -> None:
        """Test word processing functionality.

        Tests various cases of word processing including:
        - Empty word handling
        - Single character word processing
        - Words with vowels
        """
        # Test empty word
        assert ArtistIdGenerator._process_word("") == ("", "")

        # Test single character word
        assert ArtistIdGenerator._process_word("A") == ("A", "A")

        # Test word with vowels
        assert ArtistIdGenerator._process_word("HELLO") == ("HLL", "HELLO")

    def test_transliterate_japanese(self) -> None:
        """Test Japanese text transliteration.

        Verifies the correct romanization of Japanese text using pykakasi.
        """
        # Test basic Japanese text
        assert ArtistIdGenerator._transliterate_japanese("おはよう") == "OHAYOU"

        # Test mixed Japanese and Latin text
        assert ArtistIdGenerator._transliterate_japanese("Hello世界") == "HELLOSEKAI"

        # Test error handling
        assert ArtistIdGenerator._transliterate_japanese("") == ""


def test_generate_empty_input():
    """Test ID generation with empty input."""
    assert ArtistIdGenerator.generate(None) == "NOART"
    assert ArtistIdGenerator.generate("") == "NOART"


def test_generate_english():
    """Test ID generation with English text."""
    # Test basic English name
    assert ArtistIdGenerator.generate("John Smith") == "JHNSM"

    # Test name with special characters
    assert ArtistIdGenerator.generate("John-Smith") == "JHNSM"

    # Test name with numbers
    assert ArtistIdGenerator.generate("123 John Smith") == "123JH"

    # Test short name
    assert ArtistIdGenerator.generate("Jo") == "JOXXX"

    # Test long name
    assert ArtistIdGenerator.generate("John Jacob Smith") == "JHNJC"

    # Test Vowel removal
    assert ArtistIdGenerator.generate("On the Ant") == "ONTHA"


def test_generate_japanese():
    """Test ID generation with Japanese text."""
    assert ArtistIdGenerator.generate("やまだたろう") == "YMDTR"
    assert ArtistIdGenerator.generate("DJやまだ") == "DJYMD"
    assert ArtistIdGenerator.generate("すずきいちろう") == "SZKCH"
    # Test that Chinese-detected text is treated as Japanese
    assert ArtistIdGenerator.generate("山田太郎") == "YMDTR"


def test_generate_other_languages():
    """Test ID generation with other languages."""
    # Test name with diacritics
    assert ArtistIdGenerator.generate("José González") == "JSGNZ"

    # Test name with non-Latin characters
    assert ArtistIdGenerator.generate("Björk") == "BJORK"

    # Test name with special characters
    assert ArtistIdGenerator.generate("Jean-Pierre") == "JNPRR"


def test_generate_edge_cases():
    """Test ID generation with edge cases."""
    # Test name with only special characters
    assert ArtistIdGenerator.generate("!@#$%") == "XXXXX"

    # Test name with only spaces
    assert ArtistIdGenerator.generate("   ") == "NOART"

    # Test name with only numbers
    assert ArtistIdGenerator.generate("12345") == "12345"

    # Test name with mixed case
    assert ArtistIdGenerator.generate("JoHn SmItH") == "JHNSM"


def test_cached_artist_id_generator(tmp_path: Path):
    """Test cached artist ID generation."""
    # Set up test database
    db_path = tmp_path / "test.db"
    db_manager = DatabaseManager(db_path)
    db_manager.connect()
    dao = ArtistCacheDAO(db_manager.conn)

    # Create generator instance
    generator = CachedArtistIdGenerator(dao)

    # Test first-time generation
    artist_name = "John Smith"
    artist_id = generator.generate(artist_name)
    assert artist_id == "JHNSM"

    # Test cached retrieval
    cached_id = generator.generate(artist_name)
    assert cached_id == artist_id

    # Test different artist name
    other_artist = "Jane Doe"
    other_id = generator.generate(other_artist)
    assert other_id == "JANED"

    # Test case insensitivity
    mixed_case = "jOhN sMiTh"
    mixed_case_id = generator.generate(mixed_case)
    assert mixed_case_id == artist_id

    # Test None input
    none_id = generator.generate(None)
    assert none_id == "NOART"

    # Test empty string
    empty_id = generator.generate("")
    assert empty_id == "NOART"

    # Clean up
    db_manager.close()


def test_directory_generator_year_handling():
    """Test directory generation with different year scenarios."""

    def create_test_metadata(year: int) -> TrackMetadata:
        return TrackMetadata(
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            album_artist="Test Artist",
            year=year,
            track_number=1,
            disc_number=1,
            file_extension=".mp3",
        )

    # Test 1: Latest year is used
    DirectoryGenerator._album_years = {}  # Reset cache
    metadata1 = create_test_metadata(2020)
    metadata2 = create_test_metadata(2022)
    metadata3 = create_test_metadata(2021)

    DirectoryGenerator.register_album_year(metadata1)
    DirectoryGenerator.register_album_year(metadata2)
    DirectoryGenerator.register_album_year(metadata3)

    path = DirectoryGenerator.generate(metadata1)
    assert "2022_Test-Album" in str(path)

    # Test 2: Zero years are ignored
    DirectoryGenerator._album_years = {}  # Reset cache
    metadata1 = create_test_metadata(2020)
    metadata2 = create_test_metadata(0)
    metadata3 = create_test_metadata(2019)

    DirectoryGenerator.register_album_year(metadata1)
    DirectoryGenerator.register_album_year(metadata2)
    DirectoryGenerator.register_album_year(metadata3)

    path = DirectoryGenerator.generate(metadata1)
    assert "2020_Test-Album" in str(path)

    # Test 3: All tracks have no year
    DirectoryGenerator._album_years = {}  # Reset cache
    metadata1 = create_test_metadata(0)
    metadata2 = create_test_metadata(0)

    DirectoryGenerator.register_album_year(metadata1)
    DirectoryGenerator.register_album_year(metadata2)

    path = DirectoryGenerator.generate(metadata1)
    assert "0000_Test-Album" in str(path)
