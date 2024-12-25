"""Album management system for organizing music files."""

from sqlite3 import Connection
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from omym.utils.logger import logger
from omym.db.dao_albums import AlbumDAO, AlbumInfo, TrackPosition


@dataclass
class AlbumGroup:
    """Album group information."""

    album_info: AlbumInfo
    file_hashes: Set[str]
    warnings: List[str]


class AlbumManager:
    """Album manager for organizing music files."""

    def __init__(self, conn: Connection):
        """Initialize album manager.

        Args:
            conn: SQLite database connection.
        """
        self.conn = conn
        self.album_dao = AlbumDAO(conn)

    def process_files(
        self, files: Dict[str, Dict[str, Optional[str]]]
    ) -> Tuple[List[AlbumGroup], List[str]]:
        """Process files and group them into albums.

        Args:
            files: Dictionary mapping file hashes to metadata.
                The metadata dictionary contains optional string values for each field.

        Returns:
            Tuple[List[AlbumGroup], List[str]]: A tuple containing:
                - List of album groups with their associated files and warnings
                - List of global warnings that apply to the entire process
        """
        warnings: List[str] = []
        album_groups: List[AlbumGroup] = []

        # Group files by album name and album artist
        album_files: Dict[Tuple[str, str], Set[str]] = {}
        for file_hash, metadata in files.items():
            album_name = metadata.get("album")
            album_artist = metadata.get("album_artist")

            if not album_name or not album_artist:
                warnings.append(
                    f"Missing album information for file {file_hash}: "
                    f"album={album_name}, album_artist={album_artist}"
                )
                continue

            key = (album_name, album_artist)
            if key not in album_files:
                album_files[key] = set()
            album_files[key].add(file_hash)

        # Process each album group
        for (album_name, album_artist), file_hashes in album_files.items():
            group = self._process_album_group(
                album_name, album_artist, file_hashes, files
            )
            album_groups.append(group)

        return album_groups, warnings

    def _process_album_group(
        self,
        album_name: str,
        album_artist: str,
        file_hashes: Set[str],
        files: Dict[str, Dict[str, Optional[str]]],
    ) -> AlbumGroup:
        """Process an album group.

        Args:
            album_name: Album name.
            album_artist: Album artist name.
            file_hashes: Set of file hashes in the album.
            files: Dictionary mapping file hashes to metadata.
                The metadata dictionary contains optional string values for each field.

        Returns:
            AlbumGroup: Album group information containing:
                - Album info (id, name, artist, year, track/disc totals)
                - Set of file hashes in the album
                - List of warnings specific to this album
        """
        warnings: List[str] = []

        # Get or create album
        album_info = self.album_dao.get_album(album_name, album_artist)
        if not album_info:
            # Find the latest year from tracks
            year = self._get_latest_year(file_hashes, files)

            # Get total tracks and discs
            total_tracks: Optional[int] = None
            total_discs: Optional[int] = None
            for file_hash in file_hashes:
                metadata = files[file_hash]
                if "total_tracks" in metadata and metadata["total_tracks"]:
                    try:
                        total_tracks = int(metadata["total_tracks"])
                    except ValueError:
                        warnings.append(
                            f"Invalid total_tracks value for file {file_hash}: "
                            f"{metadata['total_tracks']}"
                        )
                if "total_discs" in metadata and metadata["total_discs"]:
                    try:
                        total_discs = int(metadata["total_discs"])
                    except ValueError:
                        warnings.append(
                            f"Invalid total_discs value for file {file_hash}: "
                            f"{metadata['total_discs']}"
                        )

            # Create new album
            album_id = self.album_dao.insert_album(
                album_name=album_name,
                album_artist=album_artist,
                year=year,
                total_tracks=total_tracks,
                total_discs=total_discs,
            )
            if not album_id:
                warnings.append(f"Failed to create album: {album_name}")
                return AlbumGroup(
                    album_info=AlbumInfo(
                        id=-1,
                        album_name=album_name,
                        album_artist=album_artist,
                        year=year,
                        total_tracks=total_tracks,
                        total_discs=total_discs,
                    ),
                    file_hashes=file_hashes,
                    warnings=warnings,
                )

            album_info = self.album_dao.get_album(album_name, album_artist)
            if not album_info:
                warnings.append(f"Failed to get album after creation: {album_name}")
                return AlbumGroup(
                    album_info=AlbumInfo(
                        id=-1,
                        album_name=album_name,
                        album_artist=album_artist,
                        year=year,
                        total_tracks=total_tracks,
                        total_discs=total_discs,
                    ),
                    file_hashes=file_hashes,
                    warnings=warnings,
                )

        # Register track positions
        for file_hash in file_hashes:
            metadata = files[file_hash]
            if "disc_number" not in metadata or "track_number" not in metadata:
                warnings.append(
                    f"Missing track position for file {file_hash}: "
                    f"disc={metadata.get('disc_number')}, "
                    f"track={metadata.get('track_number')}"
                )
                continue

            try:
                disc_number = int(metadata["disc_number"] or "0")
                track_number = int(metadata["track_number"] or "0")

                if not self.album_dao.insert_track_position(
                    album_info.id, disc_number, track_number, file_hash
                ):
                    warnings.append(
                        f"Failed to register track position for file {file_hash}"
                    )
            except ValueError:
                warnings.append(
                    f"Invalid track position for file {file_hash}: "
                    f"disc={metadata.get('disc_number')}, "
                    f"track={metadata.get('track_number')}"
                )

        # Check track continuity
        is_continuous, continuity_warnings = self.album_dao.check_track_continuity(
            album_info.id
        )
        if not is_continuous:
            warnings.extend(continuity_warnings)

        return AlbumGroup(
            album_info=album_info,
            file_hashes=file_hashes,
            warnings=warnings,
        )

    def _get_latest_year(
        self, file_hashes: Set[str], files: Dict[str, Dict[str, Optional[str]]]
    ) -> Optional[int]:
        """Get the latest year from a set of files.

        Args:
            file_hashes: Set of file hashes to check.
            files: Dictionary mapping file hashes to metadata.
                The metadata dictionary contains optional string values for each field.

        Returns:
            Optional[int]: Latest year if found and valid, None otherwise.
        """
        latest_year: Optional[int] = None
        for file_hash in file_hashes:
            metadata = files[file_hash]
            year_str = metadata.get("year")
            if year_str:
                try:
                    year = int(year_str)
                    if latest_year is None or year > latest_year:
                        latest_year = year
                except ValueError:
                    continue
        return latest_year
