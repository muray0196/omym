"""Summary: Adapter wiring metadata renamer ports to the path feature helpers.
Why: Keep metadata use cases decoupled from path renamer implementations via explicit ports."""

from __future__ import annotations

from pathlib import Path
from typing import final

from omym.features.metadata.usecases.ports import (
    ArtistCachePort,
    ArtistIdGeneratorPort,
    DirectoryNamingPort,
    FileNameGenerationPort,
    RenamerPorts,
)
from omym.features.path.usecases.renamer import (
    CachedArtistIdGenerator,
    DirectoryGenerator,
    FileNameGenerator,
)
from omym.shared.track_metadata import TrackMetadata


@final
class _ArtistIdGeneratorAdapter(ArtistIdGeneratorPort):
    """Wrap the path cached artist ID generator behind the metadata port."""

    def __init__(self, delegate: CachedArtistIdGenerator) -> None:
        self._delegate = delegate

    def generate(self, artist_name: str | None) -> str:
        return self._delegate.generate(artist_name)


@final
class _DirectoryGeneratorAdapter(DirectoryNamingPort):
    """Adapt ``DirectoryGenerator`` to the metadata directory port."""

    def __init__(self, delegate: DirectoryGenerator) -> None:
        self._delegate = delegate

    def register_album_year(self, metadata: TrackMetadata) -> None:
        self._delegate.register_album_year(metadata)

    def generate(self, metadata: TrackMetadata) -> Path:
        return self._delegate.generate(metadata)


@final
class _FileNameGeneratorAdapter(FileNameGenerationPort):
    """Adapt ``FileNameGenerator`` to the metadata file-name port."""

    def __init__(self, delegate: FileNameGenerator) -> None:
        self._delegate = delegate

    def register_album_track_width(self, metadata: TrackMetadata) -> None:
        FileNameGenerator.register_album_track_width(metadata)

    def generate(self, metadata: TrackMetadata) -> str:
        return self._delegate.generate(metadata)


@final
class PathRenamerAdapter:
    """Build renamer port bundles backed by the path feature renamer helpers."""

    def __init__(self, artist_cache: ArtistCachePort) -> None:
        artist_delegate = CachedArtistIdGenerator(artist_cache)
        directory_delegate = DirectoryGenerator()
        file_delegate = FileNameGenerator(artist_delegate)

        self.artist_id: ArtistIdGeneratorPort = _ArtistIdGeneratorAdapter(artist_delegate)
        self.directory: DirectoryNamingPort = _DirectoryGeneratorAdapter(directory_delegate)
        self.file_name: FileNameGenerationPort = _FileNameGeneratorAdapter(file_delegate)

    def as_ports(self) -> RenamerPorts:
        """Return the component ports packaged for use-case wiring."""

        return RenamerPorts(
            directory=self.directory,
            file_name=self.file_name,
            artist_id=self.artist_id,
        )


def build_path_renamer_ports(artist_cache: ArtistCachePort) -> RenamerPorts:
    """Create a ``RenamerPorts`` bundle backed by the path renamer helpers."""

    return PathRenamerAdapter(artist_cache).as_ports()


__all__ = ["PathRenamerAdapter", "build_path_renamer_ports"]
