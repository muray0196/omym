"""Public API for the path feature (domain + use cases)."""

from omym.shared.path_components import ComponentValue

from .domain.sanitizer import Sanitizer
from .domain.path_elements import (
    PathComponent,
    PathComponentFactory,
    AlbumArtistComponent,
    AlbumComponent,
)
from .usecases.renamer import (
    ArtistIdGenerator,
    CachedArtistIdGenerator,
    DirectoryGenerator,
    FileNameGenerator,
)
from .usecases.ports import (
    ArtistCacheWriter,
    FilterHierarchyRecord,
    FilterQueryPort,
    FilterValueRecord,
)
from .usecases.path_generator import PathGenerator, PathInfo

__all__ = [
    "Sanitizer",
    "ComponentValue",
    "PathComponent",
    "PathComponentFactory",
    "AlbumArtistComponent",
    "AlbumComponent",
    "ArtistCacheWriter",
    "ArtistIdGenerator",
    "CachedArtistIdGenerator",
    "FileNameGenerator",
    "DirectoryGenerator",
    "FilterQueryPort",
    "FilterHierarchyRecord",
    "FilterValueRecord",
    "PathGenerator",
    "PathInfo",
]
