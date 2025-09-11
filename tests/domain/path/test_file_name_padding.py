from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.path.music_file_renamer import FileNameGenerator, CachedArtistIdGenerator
from omym.infra.db.db_manager import DatabaseManager
from omym.infra.db.cache.artist_cache_dao import ArtistCacheDAO


class TestFileNamePadding:
    """Tests for album-scoped track number padding in FileNameGenerator."""

    def test_album_uses_max_digits_over_min_two(self) -> None:
        """When any track has 3 digits, pad all tracks in album to 3 digits."""
        # Arrange: two tracks in the same album with 3-digit and 2-digit numbers
        meta_103 = TrackMetadata(
            title="Track 103",
            artist="ヰ世界情緒",
            album="ヰ世界情緒-歌ってみた-Vol-3",
            album_artist="ヰ世界情緒",
            year=2024,
            disc_number=1,
            track_number=103,
            file_extension=".opus",
        )
        meta_86 = TrackMetadata(
            title="Track 86",
            artist="ヰ世界情緒",
            album="ヰ世界情緒-歌ってみた-Vol-3",
            album_artist="ヰ世界情緒",
            year=2024,
            disc_number=1,
            track_number=86,
            file_extension=".opus",
        )

        # Register album width based on all tracks
        FileNameGenerator.register_album_track_width(meta_103)
        FileNameGenerator.register_album_track_width(meta_86)

        dbm = DatabaseManager(":memory:")
        dbm.connect()
        assert dbm.conn is not None
        gen = FileNameGenerator(CachedArtistIdGenerator(ArtistCacheDAO(dbm.conn)))

        # Act
        name_103 = gen.generate(meta_103)
        name_86 = gen.generate(meta_86)

        # Assert
        assert name_103.startswith("D1_103_")
        assert name_86.startswith("D1_086_")

    def test_album_min_padding_is_two_digits(self) -> None:
        """If max digits <= 2, pad to at least 2 digits within the album."""
        meta_1 = TrackMetadata(
            title="Track 1",
            artist="Sample Artist",
            album="Min2",
            album_artist="Sample Artist",
            year=2024,
            disc_number=1,
            track_number=1,
            file_extension=".mp3",
        )
        meta_12 = TrackMetadata(
            title="Track 12",
            artist="Sample Artist",
            album="Min2",
            album_artist="Sample Artist",
            year=2024,
            disc_number=1,
            track_number=12,
            file_extension=".mp3",
        )

        FileNameGenerator.register_album_track_width(meta_1)
        FileNameGenerator.register_album_track_width(meta_12)

        dbm = DatabaseManager(":memory:")
        dbm.connect()
        assert dbm.conn is not None
        gen = FileNameGenerator(CachedArtistIdGenerator(ArtistCacheDAO(dbm.conn)))

        name_1 = gen.generate(meta_1)
        name_12 = gen.generate(meta_12)

        assert name_1.startswith("D1_01_")
        assert name_12.startswith("D1_12_")
