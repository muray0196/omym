"""Test renaming logic functionality."""

from pathlib import Path

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

    def test_generate_empty_input(self) -> None:
        """Test ID generation with empty input."""
        assert ArtistIdGenerator.generate(None) == "NOART"
        assert ArtistIdGenerator.generate("") == "NOART"

    def test_generate_english(self) -> None:
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

    def test_generate_japanese(self) -> None:
        """Test ID generation with Japanese text."""
        assert ArtistIdGenerator.generate("やまだたろう") == "YMDTR"
        assert ArtistIdGenerator.generate("DJやまだ") == "DJYMD"
        assert ArtistIdGenerator.generate("すずきいちろう") == "SZKCH"
        # Test that Chinese-detected text is treated as Japanese
        assert ArtistIdGenerator.generate("山田太郎") == "YMDTR"

    def test_generate_other_languages(self) -> None:
        """Test ID generation with other languages."""
        # Test name with diacritics
        assert ArtistIdGenerator.generate("José González") == "JSGNZ"

        # Test name with non-Latin characters
        assert ArtistIdGenerator.generate("Björk") == "BJORK"

        # Test name with special characters
        assert ArtistIdGenerator.generate("Jean-Pierre") == "JNPRR"

    def test_generate_edge_cases(self) -> None:
        """Test ID generation with edge cases."""
        # Test name with only special characters
        assert ArtistIdGenerator.generate("!@#$%") == "XXXXX"

        # Test name with only spaces
        assert ArtistIdGenerator.generate("   ") == "NOART"

        # Test name with only numbers
        assert ArtistIdGenerator.generate("12345") == "12345"

        # Test name with mixed case
        assert ArtistIdGenerator.generate("JoHn SmItH") == "JHNSM"


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

    def test_latest_year_is_used(self) -> None:
        """Test that the latest year is used for album directory."""
        # Create test metadata with unique album name
        metadata1 = self.create_test_metadata(2020, "Latest Year Album")
        metadata2 = self.create_test_metadata(2022, "Latest Year Album")
        metadata3 = self.create_test_metadata(2021, "Latest Year Album")

        # Register metadata in sequence
        DirectoryGenerator.register_album_year(metadata1)
        DirectoryGenerator.register_album_year(metadata2)
        DirectoryGenerator.register_album_year(metadata3)

        path = DirectoryGenerator.generate(metadata1)
        assert "2022_Latest-Year-Album" in str(path)

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
        assert "2020_Zero-Year-Album" in str(path)

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
