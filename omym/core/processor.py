"""Music file processing functionality."""

import shutil
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Any

from omym.core.metadata import TrackMetadata
from omym.core.metadata_extractor import MetadataExtractor
from omym.core.renaming_logic import (
    DirectoryGenerator,
    FileNameGenerator,
    CachedArtistIdGenerator,
)
from omym.db.db_manager import DatabaseManager
from omym.db.dao_artist_cache import ArtistCacheDAO
from omym.db.dao_processing_before import ProcessingBeforeDAO
from omym.db.dao_processing_after import ProcessingAfterDAO
from omym.utils.logger import logger


@dataclass
class ProcessResult:
    """Result of processing a music file.

    Attributes:
        source_path: Original path of the file.
        target_path: New path after processing, if successful.
        success: Whether the processing was successful.
        error_message: Error message if processing failed.
        dry_run: Whether this was a dry run (no actual file operations).
        file_hash: SHA-256 hash of the file content.
        metadata: Extracted metadata from the file.
        artist_id: Generated artist ID if available.
    """

    source_path: Path
    target_path: Optional[Path] = None
    success: bool = False
    error_message: Optional[str] = None
    dry_run: bool = False
    file_hash: Optional[str] = None
    metadata: Optional[TrackMetadata] = None
    artist_id: Optional[str] = None


class MusicProcessor:
    """Process music files by extracting metadata and organizing them."""

    # Supported music file extensions
    SUPPORTED_EXTENSIONS: Set[str] = {".mp3", ".flac", ".m4a", ".dsf"}

    # Size of chunks to read when calculating file hash
    HASH_CHUNK_SIZE: int = 8192  # 8KB chunks

    def __init__(self, base_path: Path, dry_run: bool = False):
        """Initialize the processor.

        Args:
            base_path: Base path for organizing music files.
            dry_run: If True, don't actually move files.
        """
        self.base_path = Path(base_path)
        self.dry_run = dry_run

        # Initialize database manager and DAOs
        self.db_manager = DatabaseManager()
        self.db_manager.connect()

        if not self.db_manager.conn:
            raise RuntimeError("Failed to connect to database")

        self.artist_cache_dao = ArtistCacheDAO(self.db_manager.conn)
        self.processing_before_dao = ProcessingBeforeDAO(self.db_manager.conn)
        self.processing_after_dao = ProcessingAfterDAO(self.db_manager.conn)

        # Initialize generators
        self.artist_id_generator = CachedArtistIdGenerator(self.artist_cache_dao)
        self.file_name_generator = FileNameGenerator(self.artist_id_generator)

    def __enter__(self) -> "MusicProcessor":
        """Context manager entry.

        Returns:
            MusicProcessor: The processor instance.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if exc_type:
            if self.db_manager.conn:
                self.db_manager.conn.rollback()
        else:
            if self.db_manager.conn:
                self.db_manager.conn.commit()
        self.db_manager.close()

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file to hash.

        Returns:
            str: Hexadecimal hash string of the file content.

        Raises:
            IOError: If the file cannot be read.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(self.HASH_CHUNK_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _check_duplicate(self, file_hash: str) -> Optional[Path]:
        """Check if a file with the same hash already exists.

        Args:
            file_hash: SHA-256 hash of the file to check.

        Returns:
            Optional[Path]: Path to existing file if found with the same hash,
                None if no duplicate exists.
        """
        # Check processing_before table for the hash
        files = self.processing_before_dao.get_all_files()
        for path, hash_value, _ in files:
            if hash_value == file_hash:
                # Get the target path from processing_after
                target_path = self.processing_after_dao.get_target_path(path)
                if target_path and target_path.exists():
                    return target_path
        return None

    def _save_file_state(
        self,
        file_path: Path,
        file_hash: str,
        metadata: TrackMetadata,
        target_path: Path,
    ) -> bool:
        """Save file state to database.

        Args:
            file_path: Original path to the file.
            file_hash: SHA-256 hash of the file content.
            metadata: Extracted metadata from the file.
            target_path: Target path where the file will be moved.

        Returns:
            bool: True if the file state was saved successfully,
                False if either insert operation failed.
        """
        try:
            # Save pre-processing state
            if not self.processing_before_dao.insert_file(
                file_path, file_hash, metadata
            ):
                return False

            # Save post-processing state
            if not self.processing_after_dao.insert_file(
                file_path, file_hash, target_path
            ):
                return False

            return True

        except Exception as e:
            logger.error("Failed to save file state: %s", e)
            return False

    def _find_available_path(self, target_path: Path) -> Path:
        """Find an available path by adding a sequence number if necessary.

        Args:
            target_path: Initial target path to check.

        Returns:
            Path: Available path, either the original if it doesn't exist,
                or a new path with a sequence number appended.
        """
        if not target_path.exists():
            return target_path

        # If file exists, add sequence number
        base = target_path.parent / target_path.stem
        ext = target_path.suffix
        counter = 1

        while True:
            new_path = Path(f"{base}_{counter}{ext}")
            if not new_path.exists():
                return new_path
            counter += 1

    def process_file(self, file_path: Path) -> ProcessResult:
        """Process a single music file.

        Args:
            file_path: Path to the music file to process.

        Returns:
            ProcessResult: Result of the processing operation, containing:
                - Original and target paths
                - Success status and any error message
                - File hash and extracted metadata
                - Generated artist ID if available
        """
        # Initialize result at the start
        result = ProcessResult(source_path=file_path, dry_run=self.dry_run)

        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            result.file_hash = file_hash

            # Check for duplicates by content
            existing_file = self._check_duplicate(file_hash)
            if existing_file:
                logger.info(
                    "Duplicate file found: '%s' is identical to '%s'",
                    file_path,
                    existing_file,
                )
                # Instead of deleting, move to a new location with sequence number
                target_path = self._find_available_path(existing_file)
                if not self.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_path))
                result.target_path = target_path
                result.success = True
                return result

            # Extract metadata
            metadata = MetadataExtractor.extract(file_path)
            if not metadata:
                raise ValueError("Failed to extract metadata")
            result.metadata = metadata

            # Generate artist ID
            if metadata.artist:
                result.artist_id = self.artist_id_generator.generate(metadata.artist)

            # Generate target directory path
            dir_path = self.base_path / DirectoryGenerator.generate(metadata)

            # Generate target file name and find available path
            file_name = self.file_name_generator.generate(metadata)
            target_path = self._find_available_path(dir_path / file_name)

            # Store target path in result
            result.target_path = target_path

            # Save file state to database
            if not self._save_file_state(file_path, file_hash, metadata, target_path):
                raise RuntimeError("Failed to save file state to database")

            # Create directory and move file if not in dry run mode
            if not self.dry_run:
                dir_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_path))

            result.success = True
            return result

        except Exception as e:
            logger.error("Failed to process file '%s': %s", file_path, e)
            result.error_message = str(e)
            return result

    def process_directory(self, directory_path: Path) -> List[ProcessResult]:
        """Process all music files in a directory and its subdirectories.

        Args:
            directory_path: Path to the directory.

        Returns:
            List[ProcessResult]: Results of processing each file.
        """
        results = []
        try:
            # First pass: collect metadata and register album years
            music_files = []
            metadata_map = {}

            for file_path in directory_path.rglob("*"):
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
                ):
                    try:
                        metadata = MetadataExtractor.extract(file_path)
                        if metadata:
                            DirectoryGenerator.register_album_year(metadata)
                            metadata_map[file_path] = metadata
                            music_files.append(file_path)
                    except Exception as e:
                        logger.error(
                            "Failed to extract metadata from '%s': %s", file_path, e
                        )
                        results.append(
                            ProcessResult(
                                source_path=file_path,
                                success=False,
                                error_message=str(e),
                                dry_run=self.dry_run,
                            )
                        )

            # Second pass: process files with collected metadata
            for file_path in music_files:
                metadata = metadata_map[file_path]
                try:
                    # Create result object
                    result = ProcessResult(source_path=file_path, dry_run=self.dry_run)
                    result.metadata = metadata

                    # Calculate file hash
                    file_hash = self._calculate_file_hash(file_path)
                    result.file_hash = file_hash

                    # Check for duplicates by content
                    existing_file = self._check_duplicate(file_hash)
                    if existing_file:
                        logger.info(
                            "Duplicate file found: '%s' is identical to '%s'",
                            file_path,
                            existing_file,
                        )
                        # Instead of deleting, move to a new location with sequence number
                        target_path = self._find_available_path(existing_file)
                        if not self.dry_run:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(file_path), str(target_path))
                        result.target_path = target_path
                        result.success = True
                        results.append(result)
                        continue

                    # Generate artist ID
                    if metadata.artist:
                        result.artist_id = self.artist_id_generator.generate(
                            metadata.artist
                        )

                    # Generate target directory path
                    dir_path = self.base_path / DirectoryGenerator.generate(metadata)

                    # Generate target file name and find available path
                    file_name = self.file_name_generator.generate(metadata)
                    target_path = self._find_available_path(dir_path / file_name)

                    # Store target path in result
                    result.target_path = target_path

                    # Save file state to database
                    if not self._save_file_state(
                        file_path, file_hash, metadata, target_path
                    ):
                        raise RuntimeError("Failed to save file state to database")

                    # Create directory and move file if not in dry run mode
                    if not self.dry_run:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file_path), str(target_path))

                    result.success = True
                    results.append(result)

                except Exception as e:
                    logger.error("Failed to process file '%s': %s", file_path, e)
                    results.append(
                        ProcessResult(
                            source_path=file_path,
                            success=False,
                            error_message=str(e),
                            dry_run=self.dry_run,
                        )
                    )

        except Exception as e:
            logger.error("Failed to process directory '%s': %s", directory_path, e)
            # Add a failed result for the directory itself
            results.append(
                ProcessResult(
                    source_path=directory_path,
                    success=False,
                    error_message=str(e),
                    dry_run=self.dry_run,
                )
            )

        return results
