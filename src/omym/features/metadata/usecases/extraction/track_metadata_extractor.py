"""Audio file metadata extraction functionality.

Where: src/omym/features/metadata/usecases/extraction/track_metadata_extractor.py
What: Provide the MetadataExtractor facade wiring Romanizer and format extractors.
Why: Offer a slim orchestration layer that routes to subcomponents after refactor.
"""

from pathlib import Path
from typing import ClassVar, Callable

from ._base_extractors import AudioFormatExtractor
from .format_extractors import (
    DsfExtractor,
    FlacExtractor,
    M4aExtractor,
    Mp3Extractor,
    OpusExtractor,
)
from .artist_romanizer import ArtistRomanizer
from ...domain.track_metadata import TrackMetadata

__all__ = [
    "MetadataExtractor",
    "Mp3Extractor",
    "FlacExtractor",
    "OpusExtractor",
    "M4aExtractor",
    "DsfExtractor",
]


class MetadataExtractor:
    """Facade class for extracting metadata from audio files.

    This class selects the appropriate extractor based on file extension.
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {".flac", ".mp3", ".m4a", ".dsf", ".opus"}

    _artist_romanizer: ClassVar[ArtistRomanizer] = ArtistRomanizer()

    # Mapping from file extension to corresponding extractor instance.
    _format_map: ClassVar[dict[str, AudioFormatExtractor]] = {
        ".mp3": Mp3Extractor(),
        ".flac": FlacExtractor(),
        ".m4a": M4aExtractor(),
        ".dsf": DsfExtractor(),
        ".opus": OpusExtractor(),
    }

    # Compatibility wrappers for tests and external patching
    @classmethod
    def _extract_mp3(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".mp3"].extract_metadata(file_path)

    @classmethod
    def _extract_flac(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".flac"].extract_metadata(file_path)

    @classmethod
    def _extract_m4a(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".m4a"].extract_metadata(file_path)

    @classmethod
    def _extract_dsf(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".dsf"].extract_metadata(file_path)

    @classmethod
    def _extract_opus(cls, file_path: Path) -> TrackMetadata:
        return cls._format_map[".opus"].extract_metadata(file_path)

    @classmethod
    def configure_romanizer(cls, romanizer: ArtistRomanizer) -> None:
        """Override the romanizer used after extraction.

        Args:
            romanizer: Romanizer instance configured for the runtime.
        """

        cls._artist_romanizer = romanizer

    @classmethod
    def extract(cls, file_path: Path) -> TrackMetadata:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file.

        Returns:
            TrackMetadata: Extracted metadata.

        Raises:
            ValueError: If the file format is unsupported.
            Exception: If extraction fails.
        """
        ext: str = file_path.suffix.lower()
        if ext not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")

        # Route through per-format methods to allow easy mocking in tests
        method_map: dict[str, Callable[[Path], TrackMetadata]] = {
            ".mp3": cls._extract_mp3,
            ".flac": cls._extract_flac,
            ".m4a": cls._extract_m4a,
            ".dsf": cls._extract_dsf,
            ".opus": cls._extract_opus,
        }

        metadata = method_map[ext](file_path)
        processed = cls._artist_romanizer.romanize_metadata(metadata)
        return processed if processed is not None else metadata
