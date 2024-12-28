"""Process music files for organization."""

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Set

from omym.core.metadata import TrackMetadata
from omym.core.metadata_extractor import MetadataExtractor
from omym.core.renaming_logic import (
    DirectoryGenerator,
    FileNameGenerator,
    CachedArtistIdGenerator,
)
from omym.db.dao_artist_cache import ArtistCacheDAO
from omym.db.dao_processing_after import ProcessingAfterDAO
from omym.db.dao_processing_before import ProcessingBeforeDAO
from omym.db.db_manager import DatabaseManager
from omym.utils.logger import logger


@dataclass
class ProcessResult:
    """Result of processing a music file."""

    source_path: Path
    target_path: Optional[Path] = None
    success: bool = False
    error_message: Optional[str] = None
    dry_run: bool = False
    file_hash: Optional[str] = None
    metadata: Optional[TrackMetadata] = None
    artist_id: Optional[str] = None


class MusicProcessor:
    """Process music files for organization."""

    # Supported file extensions
    SUPPORTED_EXTENSIONS: Set[str] = {".mp3", ".flac", ".m4a", ".dsf", ".aac", ".alac"}

    def __init__(self, base_path: Path, dry_run: bool = False) -> None:
        """Initialize music processor.

        Args:
            base_path: Base path for organizing music files.
            dry_run: Whether to perform a dry run (no actual file operations).
        """
        self.base_path = base_path
        self.dry_run = dry_run

        # Initialize database connection
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        if self.db_manager.conn is None:
            raise RuntimeError("Failed to connect to database")

        # Initialize DAOs
        self.before_dao = ProcessingBeforeDAO(self.db_manager.conn)
        self.after_dao = ProcessingAfterDAO(self.db_manager.conn)
        self.artist_dao = ArtistCacheDAO(self.db_manager.conn)

        # Initialize generators
        self.artist_id_generator = CachedArtistIdGenerator(self.artist_dao)
        self.directory_generator = DirectoryGenerator()
        self.file_name_generator = FileNameGenerator(self.artist_id_generator)

    def process_directory(
        self, directory: Path, progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessResult]:
        """Process all music files in a directory.

        Args:
            directory: Directory to process.
            progress_callback: Optional callback for progress updates.

        Returns:
            List of ProcessResult objects.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        results: List[ProcessResult] = []
        total_files = sum(
            1 for f in directory.rglob("*") if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )
        processed_files = 0

        if total_files == 0:
            logger.warning("No supported music files found in directory: %s", directory)
            return []

        try:
            # Begin transaction for the entire directory
            if self.db_manager.conn is not None:
                self.db_manager.conn.execute("BEGIN TRANSACTION")

            for file_path in directory.rglob("*"):
                if not file_path.is_file() or file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue

                logger.info("Processing %s", file_path)

                try:
                    # Calculate file hash
                    file_hash = self._calculate_file_hash(file_path)

                    # Check if file has already been processed
                    if self.before_dao.check_file_exists(file_hash):
                        logger.info("Already processed %s", file_path.name)
                        continue

                    # Process file
                    result = self.process_file(file_path)
                    results.append(result)

                    # Update progress
                    processed_files += 1
                    if progress_callback:
                        progress_callback(processed_files, total_files)

                except Exception as e:
                    error_message = str(e) if str(e) else type(e).__name__
                    logger.error("Error processing file '%s': %s", file_path, error_message)
                    results.append(
                        ProcessResult(
                            source_path=file_path,
                            success=False,
                            error_message=error_message,
                            dry_run=self.dry_run,
                        )
                    )

            # Clean up empty directories if not in dry run mode
            if not self.dry_run:
                self._cleanup_empty_directories(directory)

            # Commit all changes to database
            if self.db_manager.conn is not None:
                self.db_manager.conn.commit()
                logger.info("Successfully committed all changes to database")

        except Exception as e:
            error_message = str(e) if str(e) else type(e).__name__
            logger.error("Error processing directory '%s': %s", directory, error_message)
            if self.db_manager.conn is not None:
                self.db_manager.conn.rollback()

        return results

    def _cleanup_empty_directories(self, directory: Path) -> None:
        """Clean up empty directories.

        Args:
            directory: Directory to clean up.
        """
        for root, _, _ in os.walk(str(directory), topdown=False):
            try:
                root_path = Path(root)
                if root_path.exists() and not any(root_path.iterdir()):
                    root_path.rmdir()
            except OSError:
                continue

    def _generate_target_path(self, file_path: Path, metadata: TrackMetadata) -> Optional[Path]:
        """Generate target path for a file.

        Args:
            file_path: Source file path.
            metadata: Track metadata.

        Returns:
            Target path if successful, None otherwise.
        """
        try:
            # Generate target path components
            dir_path = self.directory_generator.generate(metadata)
            file_name = self.file_name_generator.generate(metadata)
            if not dir_path or not file_name:
                return None

            # Find available path
            target_path = self._find_available_path(self.base_path / dir_path / file_name)
            return target_path

        except Exception as e:
            logger.error("Error generating target path: %s", e)
            return None

    def process_file(self, file_path: Path) -> ProcessResult:
        """Process a single music file.

        Args:
            file_path: Path to the music file.

        Returns:
            ProcessResult object containing the result of processing.
        """
        file_hash: Optional[str] = None
        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)

            # Check if file has already been processed
            if self.before_dao.check_file_exists(file_hash):
                # Get existing target path
                target_path = self.before_dao.get_target_path(file_hash)
                if target_path and target_path.exists():
                    logger.info("File already processed: %s -> %s", file_path, target_path)
                    return ProcessResult(
                        source_path=file_path,
                        target_path=target_path,
                        success=True,
                        dry_run=self.dry_run,
                        file_hash=file_hash,
                    )

            # Extract metadata
            metadata = MetadataExtractor.extract(file_path)
            if not metadata:
                raise ValueError("Failed to extract metadata")

            # Generate target path
            target_path = self._generate_target_path(file_path, metadata)
            if not target_path:
                raise ValueError("Failed to generate target path")

            # Save file state to database
            if not self.before_dao.insert_file(file_hash, file_path):
                raise ValueError("Failed to save file state to database")

            # Move file if not in dry run mode
            if not self.dry_run:
                # Create target directory
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Move file
                logger.info("Moving file from %s to %s", file_path, target_path)
                shutil.move(str(file_path), str(target_path))

                # Save after state to database
                if not self.after_dao.insert_file(file_hash, file_path, target_path):
                    raise ValueError("Failed to save file state to database")

            return ProcessResult(
                source_path=file_path,
                target_path=target_path,
                success=True,
                dry_run=self.dry_run,
                file_hash=file_hash,
                metadata=metadata,
            )

        except Exception as e:
            error_message = str(e) if str(e) else type(e).__name__
            logger.error("Error processing file '%s': %s", file_path, error_message)
            return ProcessResult(
                source_path=file_path,
                success=False,
                error_message=error_message,
                dry_run=self.dry_run,
                file_hash=file_hash,
            )

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file.

        Returns:
            SHA-256 hash of file.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _find_available_path(self, target_path: Path) -> Path:
        """Find an available path by appending a sequence number if necessary.

        Args:
            target_path: Target path to check.

        Returns:
            Available path.
        """
        if not target_path.exists():
            return target_path

        base = target_path.parent / target_path.stem
        ext = target_path.suffix
        counter = 1

        while True:
            new_path = Path(f"{base}_{counter}{ext}")
            if not new_path.exists():
                return new_path
            counter += 1

    def _save_file_state(
        self,
        file_path: Path,
        file_hash: str,
        metadata: TrackMetadata,
        target_path: Path,
    ) -> bool:
        """Save file state to database.

        Args:
            file_path: Source file path.
            file_hash: File hash.
            metadata: File metadata.
            target_path: Target file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Save file state
            if self.db_manager.conn is None:
                return False

            # Save to processing_before table
            if not self.before_dao.insert_file(file_hash, file_path):
                return False

            # Save to processing_after table
            if not self.after_dao.insert_file(file_hash, file_path, target_path):
                return False

            # Save artist ID to cache
            if metadata.artist:
                artist_id = self.artist_id_generator.generate(metadata.artist)
                if artist_id and not self.artist_dao.insert_artist_id(metadata.artist, artist_id):
                    return False

            return True

        except Exception as e:
            logger.error("Database error: %s", e)
            return False
