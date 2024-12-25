"""Data access object for pre-processing state."""

from pathlib import Path
from sqlite3 import Connection
from typing import List, Optional, Tuple

from omym.core.metadata import TrackMetadata
from omym.utils.logger import logger


class ProcessingBeforeDAO:
    """Data access object for pre-processing state.

    This class manages the storage and retrieval of music file metadata
    before processing. It ensures that file information is properly tracked
    and can be accessed throughout the processing pipeline.
    """

    def __init__(self, conn: Connection):
        """Initialize DAO.

        Args:
            conn: SQLite database connection.
        """
        self.conn = conn

    def insert_file(
        self, file_path: Path, file_hash: str, metadata: TrackMetadata
    ) -> bool:
        """Insert file metadata into pre-processing state.

        If a file with the same path already exists, updates its metadata
        and sets the updated_at timestamp.

        Args:
            file_path: Path to the music file.
            file_hash: Hash of the file content.
            metadata: Extracted metadata from the file.

        Returns:
            bool: True if successful, False if the operation failed.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO processing_before (
                    file_path, file_hash, title, artist, album,
                    album_artist, genre, year, track_number, track_total,
                    disc_number, disc_total
                ) VALUES (
                    :path, :hash,
                    :title, :artist, :album, :album_artist, :genre,
                    CAST(:year AS INTEGER),
                    CAST(:track_number AS INTEGER),
                    CAST(:track_total AS INTEGER),
                    CAST(:disc_number AS INTEGER),
                    CAST(:disc_total AS INTEGER)
                )
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    title = excluded.title,
                    artist = excluded.artist,
                    album = excluded.album,
                    album_artist = excluded.album_artist,
                    genre = excluded.genre,
                    year = excluded.year,
                    track_number = excluded.track_number,
                    track_total = excluded.track_total,
                    disc_number = excluded.disc_number,
                    disc_total = excluded.disc_total,
                    updated_at = CURRENT_TIMESTAMP
                """,
                {
                    "path": str(file_path),
                    "hash": file_hash,
                    "title": metadata.title,
                    "artist": metadata.artist,
                    "album": metadata.album,
                    "album_artist": metadata.album_artist,
                    "genre": metadata.genre,
                    "year": metadata.year,
                    "track_number": metadata.track_number,
                    "track_total": metadata.track_total,
                    "disc_number": metadata.disc_number,
                    "disc_total": metadata.disc_total,
                },
            )
            self.conn.commit()
            return True

        except Exception as e:
            logger.error("Failed to insert file metadata: %s", e)
            self.conn.rollback()
            return False

    def get_file_metadata(self, file_path: Path) -> Optional[Tuple[str, TrackMetadata]]:
        """Get file metadata from pre-processing state.

        Args:
            file_path: Path to the music file.

        Returns:
            Optional[Tuple[str, TrackMetadata]]: Tuple of (file_hash, metadata) if found,
                None if the file doesn't exist or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT file_hash, title, artist, album, album_artist,
                       genre, year, track_number, track_total,
                       disc_number, disc_total
                FROM processing_before
                WHERE file_path = :path
                """,
                {"path": str(file_path)},
            )
            result = cursor.fetchone()
            if result:
                file_hash = result[0]
                metadata = TrackMetadata(
                    title=result[1],
                    artist=result[2],
                    album=result[3],
                    album_artist=result[4],
                    genre=result[5],
                    year=result[6],
                    track_number=result[7],
                    track_total=result[8],
                    disc_number=result[9],
                    disc_total=result[10],
                )
                return file_hash, metadata
            return None

        except Exception as e:
            logger.error("Failed to get file metadata: %s", e)
            return None

    def get_all_files(self) -> List[Tuple[Path, str, TrackMetadata]]:
        """Get all files from pre-processing state.

        Returns:
            List[Tuple[Path, str, TrackMetadata]]: List of (file_path, file_hash, metadata).
            Returns an empty list if no files exist or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT file_path, file_hash, title, artist, album,
                       album_artist, genre, year, track_number, track_total,
                       disc_number, disc_total
                FROM processing_before
                ORDER BY file_path
                """
            )
            results = []
            for row in cursor.fetchall():
                file_path = Path(row[0])
                file_hash = row[1]
                metadata = TrackMetadata(
                    title=row[2],
                    artist=row[3],
                    album=row[4],
                    album_artist=row[5],
                    genre=row[6],
                    year=row[7],
                    track_number=row[8],
                    track_total=row[9],
                    disc_number=row[10],
                    disc_total=row[11],
                )
                results.append((file_path, file_hash, metadata))
            return results

        except Exception as e:
            logger.error("Failed to get all files: %s", e)
            return []

    def delete_file(self, file_path: Path) -> bool:
        """Delete file from pre-processing state.

        Args:
            file_path: Path to the music file.

        Returns:
            bool: True if successful, False if the file doesn't exist or on error.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM processing_before WHERE file_path = :path",
                {"path": str(file_path)},
            )
            self.conn.commit()
            return True

        except Exception as e:
            logger.error("Failed to delete file: %s", e)
            self.conn.rollback()
            return False
