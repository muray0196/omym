"""Music file processing functionality."""

import shutil
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

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
    SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".dsf"}

    def __init__(self, base_path: Path, dry_run: bool = False) -> None:
        """Initialize processor.

        Args:
            base_path: Base path for organizing files.
            dry_run: Whether to perform a dry run.
        """
        self.base_path = base_path
        self.dry_run = dry_run
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        if self.db_manager.conn is None:
            raise RuntimeError("Failed to connect to database")
        self.artist_cache_dao = ArtistCacheDAO(self.db_manager.conn)
        self.artist_id_generator = CachedArtistIdGenerator(self.artist_cache_dao)
        self.file_name_generator = FileNameGenerator(self.artist_id_generator)

    def process_directory(self, directory: Path) -> List[ProcessResult]:
        """Process all music files in a directory.

        Args:
            directory: Directory containing music files.

        Returns:
            List[ProcessResult]: Results of processing each file.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        results: List[ProcessResult] = []
        for file_path in directory.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ):
                result = self.process_file(file_path)
                results.append(result)

        return results

    def process_file(self, file_path: Path) -> ProcessResult:
        """Process a single music file.

        Args:
            file_path: Path to the music file.

        Returns:
            ProcessResult: Result of the processing operation.
        """
        # Initialize result with default values
        result = ProcessResult(
            source_path=file_path,
            success=False,
            dry_run=self.dry_run,
        )

        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            result.file_hash = file_hash

            # Extract metadata
            metadata = MetadataExtractor.extract(file_path)
            result.metadata = metadata

            # Generate artist ID if artist is present
            if metadata.artist:
                artist_id = self.artist_id_generator.generate(metadata.artist)
                result.artist_id = artist_id

            # Generate target path
            dir_path = DirectoryGenerator.generate(metadata)
            file_name = self.file_name_generator.generate(metadata)
            target_path = self._find_available_path(
                self.base_path / dir_path / file_name
            )
            result.target_path = target_path

            # Save file state to database
            if not self._save_file_state(file_path, file_hash, metadata, target_path):
                raise RuntimeError("Failed to save file state to database")

            # Create directory and move file if not in dry run mode
            if not self.dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_path))

            result.success = True

        except Exception as e:
            logger.error("Failed to process file '%s': %s", file_path, e)
            result.error_message = str(e)

        return result

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file.

        Returns:
            str: Hexadecimal hash string.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _find_available_path(self, target_path: Path) -> Path:
        """Find an available path by adding a sequence number if needed.

        Args:
            target_path: Initial target path.

        Returns:
            Path: Available path that doesn't exist.
        """
        if not target_path.exists():
            return target_path

        base = target_path.parent / target_path.stem
        suffix = target_path.suffix
        counter = 1

        while True:
            new_path = Path(f"{base}_{counter}{suffix}")
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
            file_path: Original file path.
            file_hash: File content hash.
            metadata: Extracted metadata.
            target_path: Target path after processing.

        Returns:
            bool: True if successful, False otherwise.
        """
        if self.db_manager.conn is None:
            return False

        try:
            # Save to processing_before table
            before_dao = ProcessingBeforeDAO(self.db_manager.conn)
            if not before_dao.insert_file(file_path, file_hash, metadata):
                return False

            # Save to processing_after table
            after_dao = ProcessingAfterDAO(self.db_manager.conn)
            if not after_dao.insert_file(file_path, file_hash, target_path):
                return False

            return True

        except Exception as e:
            logger.error("Failed to save file state: %s", e)
            return False
