"""Process music files for organization."""

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ClassVar, final

from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.metadata.track_metadata_extractor import MetadataExtractor
from omym.domain.path.music_file_renamer import (
    DirectoryGenerator,
    FileNameGenerator,
    CachedArtistIdGenerator,
)
from omym.infra.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.infra.db.daos.processing_after_dao import ProcessingAfterDAO
from omym.infra.db.daos.processing_before_dao import ProcessingBeforeDAO
from omym.infra.db.db_manager import DatabaseManager
from omym.infra.logger.logger import logger
from omym.infra.musicbrainz.client import configure_romanization_cache


@dataclass
class ProcessResult:
    """Result of processing a music file."""

    source_path: Path
    target_path: Path | None = None
    success: bool = False
    error_message: str | None = None
    dry_run: bool = False
    file_hash: str | None = None
    metadata: TrackMetadata | None = None
    artist_id: str | None = None


@final
class MusicProcessor:
    """Process music files for organization."""

    # Supported file extensions.
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".mp3", ".flac", ".m4a", ".dsf", ".aac", ".alac", ".opus"}

    base_path: Path
    dry_run: bool
    db_manager: DatabaseManager
    before_dao: ProcessingBeforeDAO
    after_dao: ProcessingAfterDAO
    artist_dao: ArtistCacheDAO
    artist_id_generator: CachedArtistIdGenerator
    directory_generator: DirectoryGenerator
    file_name_generator: FileNameGenerator

    def __init__(self, base_path: Path, dry_run: bool = False) -> None:
        """Initialize music processor.

        Args:
            base_path: Base path for organizing music files.
            dry_run: Whether to perform a dry run (no actual file operations).
        """
        self.base_path = base_path
        self.dry_run = dry_run

        # Initialize database connection.
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        if self.db_manager.conn is None:
            raise RuntimeError("Failed to connect to database")

        # Initialize DAOs.
        self.before_dao = ProcessingBeforeDAO(self.db_manager.conn)
        self.after_dao = ProcessingAfterDAO(self.db_manager.conn)
        self.artist_dao = ArtistCacheDAO(self.db_manager.conn)
        configure_romanization_cache(self.artist_dao)

        # Initialize generators.
        self.artist_id_generator = CachedArtistIdGenerator(self.artist_dao)
        self.directory_generator = DirectoryGenerator()
        self.file_name_generator = FileNameGenerator(self.artist_id_generator)

    def process_directory(
        self,
        directory: Path,
        progress_callback: Callable[[int, int, Path], None] | None = None,
    ) -> list[ProcessResult]:
        """Process all music files in a directory.

        Args:
            directory: Directory to process.
            progress_callback: Optional callback for progress updates. Signature:
                (processed_count, total_count, current_file_path)

        Returns:
            List of ProcessResult objects.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        results: list[ProcessResult] = []
        # Build a list of supported files.
        supported_files = [f for f in directory.rglob("*") if self._is_supported(f)]
        total_files = len(supported_files)
        if total_files == 0:
            logger.warning("No supported music files found in directory: %s", directory)
            return results

        # Pre-scan metadata to register album years across the whole directory.
        # This ensures the album-level earliest year is known before generating any paths,
        # avoiding transient splits like 2020_/2024_ for the same album based on processing order.
        for pre_file in supported_files:
            try:
                meta = MetadataExtractor.extract(pre_file)
                self.directory_generator.register_album_year(meta)
                # Register album-level track width for consistent padding
                FileNameGenerator.register_album_track_width(meta)
            except Exception:
                # Best-effort: failure to read one file's metadata must not block processing
                continue

        processed_count = 0
        try:
            # Begin transaction for the entire directory.
            conn = self.db_manager.conn
            if conn is None:
                raise RuntimeError("Database connection is not initialized")
            _ = conn.execute("BEGIN TRANSACTION")

            for current_file in supported_files:
                logger.info("Processing %s", current_file)
                try:
                    file_hash = self._calculate_file_hash(current_file)
                    # Skip files that have already been processed.
                    if self.before_dao.check_file_exists(file_hash):
                        logger.info("Already processed %s", current_file.name)
                        continue

                    result = self.process_file(current_file)
                    results.append(result)
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_files, current_file)

                except Exception as e:
                    error_message = str(e) if str(e) else type(e).__name__
                    logger.error("Error processing file '%s': %s", current_file, error_message)
                    results.append(
                        ProcessResult(
                            source_path=current_file,
                            success=False,
                            error_message=error_message,
                            dry_run=self.dry_run,
                        )
                    )

            if not self.dry_run:
                self._cleanup_empty_directories(directory)

            conn = self.db_manager.conn
            if conn is None:
                raise RuntimeError("Database connection is not initialized")
            conn.commit()
            logger.info("Successfully committed all changes to database")

        except Exception as e:
            error_message = str(e) if str(e) else type(e).__name__
            logger.error("Error processing directory '%s': %s", directory, error_message)
            conn = self.db_manager.conn
            if conn is not None:
                conn.rollback()

        return results

    def process_file(self, file_path: Path) -> ProcessResult:
        """Process a single music file.

        Args:
            file_path: Path to the music file.

        Returns:
            ProcessResult object containing the result of processing.
        """
        file_hash: str | None = None
        try:
            # Calculate file hash.
            file_hash = self._calculate_file_hash(file_path)

            if self.before_dao.check_file_exists(file_hash):
                # Get existing target path.
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

            # Extract metadata.
            metadata = MetadataExtractor.extract(file_path)
            if not metadata:
                raise ValueError("Failed to extract metadata")

            # Generate target path.
            target_path = self._generate_target_path(metadata)
            if not target_path:
                raise ValueError("Failed to generate target path")

            # Save file state.
            if not self.before_dao.insert_file(file_hash, file_path):
                raise ValueError("Failed to save file state to database")

            # If not in dry run mode, move the file and record updated state.
            if not self.dry_run:
                self._move_file(file_path, target_path)
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

    def _is_supported(self, file: Path) -> bool:
        """Check if the given file has a supported extension.

        Args:
            file: File path to check.

        Returns:
            True if file is supported; otherwise, False.
        """
        return file.is_file() and file.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _move_file(self, src_path: Path, dest_path: Path) -> None:
        """Move a file from the source path to the target path.

        Args:
            src_path: Source file path.
            dest_path: Target file path.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Moving file from %s to %s", src_path, dest_path)
        _ = shutil.move(str(src_path), str(dest_path))

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

    def _generate_target_path(self, metadata: TrackMetadata) -> Path | None:
        """Generate target path for a file based on its metadata.

        Args:
            metadata: Track metadata.

        Returns:
            Target path if successful, None otherwise.
        """
        try:
            # Generate components for target directory and file name.
            dir_path = self.directory_generator.generate(metadata)
            file_name = self.file_name_generator.generate(metadata)
            if not dir_path or not file_name:
                return None

            target_path = self._find_available_path(self.base_path / dir_path / file_name)
            return target_path

        except Exception as e:
            logger.error("Error generating target path: %s", e)
            return None

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file.

        Returns:
            Hexadecimal hash string.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _find_available_path(self, target_path: Path) -> Path:
        """Find an available file path by appending a number if needed.

        Args:
            target_path: Initial target path.

        Returns:
            Available file path.
        """
        if not target_path.exists():
            return target_path

        base = target_path.parent / target_path.stem
        extension = target_path.suffix
        counter = 1

        while True:
            new_path = Path(f"{base} ({counter}){extension}")
            if not new_path.exists():
                return new_path
            counter += 1
