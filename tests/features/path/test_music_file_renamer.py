"""Test renaming logic functionality."""

from pathlib import Path

from omym.features.path.usecases.renamer import (
    ArtistIdGenerator,
    CachedArtistIdGenerator,
    DirectoryGenerator,
)
from omym.features.metadata.domain.track_metadata import TrackMetadata
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.db.db_manager import DatabaseManager


class TestArtistIdGenerator:
    """Test cases for ArtistIdGenerator class."""

    def test_generate_empty_input(self) -> None:
        """Test ID generation with empty input."""
        assert ArtistIdGenerator.generate(None) == "NOART"
        assert ArtistIdGenerator.generate("") == "NOART"

    def test_generate_english(self) -> None:
        """Test ID generation with English text."""
        # Test basic English name
        assert ArtistIdGenerator.generate("John Smith") == "JOHNSMTH"

        # Test name with special characters
        assert ArtistIdGenerator.generate("John-Smith") == "JOHNSMTH"

        # Test name with numbers
        assert ArtistIdGenerator.generate("123 John Smith") == "123JHNSM"

        # Test short name (no padding)
        assert ArtistIdGenerator.generate("Jo") == "JO"

        # Test long name
        assert ArtistIdGenerator.generate("John Jacob Smith") == "JHNJCBSM"

        # Test Vowel removal
        assert ArtistIdGenerator.generate("On the Ant") == "ONTHEANT"

    def test_generate_multi_artist(self) -> None:
        """Multiple artists receive length-balanced quotas while preserving order."""

        assert ArtistIdGenerator.generate("John Smith, Jane Doe") == "JHSMJAND"

    def test_generate_multi_artist_hyphenated_segments(self) -> None:
        """Hyphen-separated segments remain balanced but respect input order."""

        assert ArtistIdGenerator.generate("Michael Jackson, More More Jump") == "MCJCMRMJ"

    def test_generate_multi_artist_preserves_initial_vowel(self) -> None:
        """Initial vowels for subsequent artists remain in the identifier."""

        assert ArtistIdGenerator.generate("kaf, isekaijoucho") == "KAFISKJC"

    def test_generate_multi_artist_respects_input_order(self) -> None:
        """Switching artist order changes allocation as expected."""

        assert ArtistIdGenerator.generate("isekaijoucho, kaf") == "ISKJCKAF"
        assert ArtistIdGenerator.generate("Jane Doe, John Smith") == "JANDJHSM"

    def test_generate_multi_artist_inserts_vowels_in_place(self) -> None:
        """Fallback vowels re-enter at their original positions within each artist."""

        assert ArtistIdGenerator.generate("kaf, kafu") == "KAFKAFU"

    def test_generate_multi_artist_round_robin_segments(self) -> None:
        """Round-robin allocation mirrors single-artist progression across artists."""

        artists = "Kuramoto China, Shirosawa Hiro, Tsukimura Temari"
        assert ArtistIdGenerator.generate(artists) == "KRCSHHTT"

    def test_generate_japanese(self) -> None:
        """Test ID generation with Japanese text."""
        assert ArtistIdGenerator.generate("やまだたろう") == "YAMADATR"
        assert ArtistIdGenerator.generate("DJやまだ") == "DJYAMADA"
        assert ArtistIdGenerator.generate("すずきいちろう") == "SUZUKCHR"
        # Test that Chinese-detected text is treated as Japanese
        assert ArtistIdGenerator.generate("山田太郎") == "YAMADATR"

    def test_generate_other_languages(self) -> None:
        """Test ID generation with other languages."""
        # Test name with diacritics
        assert ArtistIdGenerator.generate("José González") == "JOSGNZLZ"

        # Test name with non-Latin characters
        assert ArtistIdGenerator.generate("Björk") == "BJORK"

        # Test name with special characters
        assert ArtistIdGenerator.generate("Jean-Pierre") == "JEANPIRR"

    def test_generate_edge_cases(self) -> None:
        """Test ID generation with edge cases."""
        # Test name with only special characters
        assert ArtistIdGenerator.generate("!@#$%") == ArtistIdGenerator.FALLBACK_ID

        # Test name with only spaces
        assert ArtistIdGenerator.generate("   ") == "NOART"

        # Test name with only numbers
        assert ArtistIdGenerator.generate("12345") == "12345"

        # Test name with mixed case
        assert ArtistIdGenerator.generate("JoHn SmItH") == "JOHNSMTH"

    def test_generate_sparse_consonants(self) -> None:
        """Scarce-consonant names retain all words within the configured cap."""

        assert ArtistIdGenerator.generate("Fujii Kaze") == "FUJIKAZE"

        assert ArtistIdGenerator.generate("Michael-Jackson") == "MCHLJCKS"

        abc_id = ArtistIdGenerator.generate("A-B-C")
        assert abc_id == "ABC"
        assert all(char in abc_id for char in "ABC")
        assert len(abc_id) <= ArtistIdGenerator.ID_LENGTH


class TestCachedArtistIdGenerator:
    """Test cases for CachedArtistIdGenerator class."""

    def test_cached_artist_id_generator(self, tmp_path: Path) -> None:
        """Test cached artist ID generation.

        Args:
            tmp_path: Temporary directory path fixture.
        """
        # Set up test database
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(db_path)
        db_manager.connect()

        if not db_manager.conn:
            raise RuntimeError("Failed to connect to database")

        dao = ArtistCacheDAO(db_manager.conn)

        # Create generator instance
        generator = CachedArtistIdGenerator(dao)

        # Test first-time generation
        artist_name = "John Smith"
        artist_id = generator.generate(artist_name)
        assert artist_id == "JOHNSMTH"

        # Test cached retrieval
        cached_id = generator.generate(artist_name)
        assert cached_id == artist_id

        # Test different artist name
        other_artist = "Jane Doe"
        other_id = generator.generate(other_artist)
        assert other_id == "JANEDOE"

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


class TestDirectoryGenerator:
    """Test cases for DirectoryGenerator class."""

    @staticmethod
    def create_test_metadata(year: int, album: str = "Test Album") -> TrackMetadata:
        """Create test metadata with specified year and album.

        Args:
            year: Year to use in metadata.
            album: Album name to use in metadata.

        Returns:
            TrackMetadata: Test metadata instance.
        """
        return TrackMetadata(
            title="Test Track",
            artist="Test Artist",
            album=album,
            album_artist="Test Artist",
            year=year,
            track_number=1,
            disc_number=1,
            file_extension=".mp3",
        )

    def test_earliest_year_is_used(self) -> None:
        """Test that the earliest year is used for album directory."""
        # Create test metadata with unique album name
        metadata1 = self.create_test_metadata(2020, "Latest Year Album")
        metadata2 = self.create_test_metadata(2022, "Latest Year Album")
        metadata3 = self.create_test_metadata(2021, "Latest Year Album")

        # Register metadata in sequence
        DirectoryGenerator.register_album_year(metadata1)
        DirectoryGenerator.register_album_year(metadata2)
        DirectoryGenerator.register_album_year(metadata3)

        path = DirectoryGenerator.generate(metadata1)
        assert "2020_Latest-Year-Album" in str(path)

    def test_zero_years_are_ignored(self) -> None:
        """Test that zero years are ignored when determining album year."""
        # Create test metadata with unique album name
        metadata1 = self.create_test_metadata(2020, "Zero Year Album")
        metadata2 = self.create_test_metadata(0, "Zero Year Album")
        metadata3 = self.create_test_metadata(2019, "Zero Year Album")

        # Register metadata in sequence
        DirectoryGenerator.register_album_year(metadata1)
        DirectoryGenerator.register_album_year(metadata2)
        DirectoryGenerator.register_album_year(metadata3)

        path = DirectoryGenerator.generate(metadata1)
        assert "2019_Zero-Year-Album" in str(path)

    def test_all_tracks_have_no_year(self) -> None:
        """Test handling of albums where all tracks have no year."""
        # Create test metadata with unique album name
        metadata1 = self.create_test_metadata(0, "No Year Album")
        metadata2 = self.create_test_metadata(0, "No Year Album")

        # Register metadata in sequence
        DirectoryGenerator.register_album_year(metadata1)
        DirectoryGenerator.register_album_year(metadata2)

        path = DirectoryGenerator.generate(metadata1)
        assert "0000_No-Year-Album" in str(path)
