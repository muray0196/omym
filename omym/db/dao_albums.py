"""Data access object for album management."""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from omym.utils.logger import logger


@dataclass
class AlbumInfo:
    """Album information."""

    id: int
    album_name: str
    album_artist: str
    year: Optional[int]
    total_tracks: Optional[int]
    total_discs: Optional[int]


@dataclass
class TrackPosition:
    """Track position information."""

    disc_number: int
    track_number: int
    file_hash: str


class AlbumDAO:
    """Data access object for album management."""

    def __init__(self, conn):
        """Initialize DAO.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def insert_album(
        self,
        album_name: str,
        album_artist: str,
        year: Optional[int] = None,
        total_tracks: Optional[int] = None,
        total_discs: Optional[int] = None,
    ) -> Optional[int]:
        """Insert an album.

        Args:
            album_name: Name of the album.
            album_artist: Album artist name.
            year: Album year.
            total_tracks: Total number of tracks.
            total_discs: Total number of discs.

        Returns:
            Optional[int]: Album ID if successful, None otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO albums (
                    album_name, album_artist, year, total_tracks, total_discs
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (album_name, album_artist, year, total_tracks, total_discs),
            )
            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error("Failed to insert album: %s", e)
            self.conn.rollback()
            return None

    def get_album(self, album_name: str, album_artist: str) -> Optional[AlbumInfo]:
        """Get album information.

        Args:
            album_name: Name of the album.
            album_artist: Album artist name.

        Returns:
            Optional[AlbumInfo]: Album information if found.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, year, total_tracks, total_discs
                FROM albums
                WHERE album_name = ? AND album_artist = ?
                """,
                (album_name, album_artist),
            )
            row = cursor.fetchone()
            if row:
                return AlbumInfo(
                    id=row[0],
                    album_name=album_name,
                    album_artist=album_artist,
                    year=row[1],
                    total_tracks=row[2],
                    total_discs=row[3],
                )
            return None

        except Exception as e:
            logger.error("Failed to get album: %s", e)
            return None

    def insert_track_position(
        self, album_id: int, disc_number: int, track_number: int, file_hash: str
    ) -> bool:
        """Insert a track position.

        Args:
            album_id: Album ID.
            disc_number: Disc number.
            track_number: Track number.
            file_hash: File hash.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO track_positions (
                    album_id, disc_number, track_number, file_hash
                ) VALUES (?, ?, ?, ?)
                """,
                (album_id, disc_number, track_number, file_hash),
            )
            self.conn.commit()
            return True

        except Exception as e:
            logger.error("Failed to insert track position: %s", e)
            self.conn.rollback()
            return False

    def get_album_tracks(self, album_id: int) -> List[TrackPosition]:
        """Get all tracks in an album.

        Args:
            album_id: Album ID.

        Returns:
            List[TrackPosition]: List of track positions.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT disc_number, track_number, file_hash
                FROM track_positions
                WHERE album_id = ?
                ORDER BY disc_number, track_number
                """,
                (album_id,),
            )
            return [
                TrackPosition(
                    disc_number=row[0],
                    track_number=row[1],
                    file_hash=row[2],
                )
                for row in cursor.fetchall()
            ]

        except Exception as e:
            logger.error("Failed to get album tracks: %s", e)
            return []

    def check_track_continuity(self, album_id: int) -> Tuple[bool, List[str]]:
        """Check track number continuity in an album.

        Args:
            album_id: Album ID.

        Returns:
            Tuple[bool, List[str]]: (is_continuous, list of warnings)
        """
        tracks = self.get_album_tracks(album_id)
        if not tracks:
            return False, ["No tracks found in album"]

        warnings = []
        disc_tracks: Dict[int, List[int]] = {}

        # Group tracks by disc
        for track in tracks:
            if track.disc_number not in disc_tracks:
                disc_tracks[track.disc_number] = []
            disc_tracks[track.disc_number].append(track.track_number)

        # Check each disc
        for disc_num, track_nums in disc_tracks.items():
            track_nums.sort()
            expected = list(range(1, len(track_nums) + 1))
            if track_nums != expected:
                missing = set(expected) - set(track_nums)
                if missing:
                    warnings.append(
                        f"Missing tracks in disc {disc_num}: {sorted(missing)}"
                    )

        # Check disc number continuity
        disc_nums = sorted(disc_tracks.keys())
        expected_discs = list(range(1, len(disc_nums) + 1))
        if disc_nums != expected_discs:
            missing = set(expected_discs) - set(disc_nums)
            if missing:
                warnings.append(f"Missing discs: {sorted(missing)}")

        return len(warnings) == 0, warnings
