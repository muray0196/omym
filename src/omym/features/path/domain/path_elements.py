"""Domain-level path component behavior for building file paths.

This module defines the polymorphic path component abstractions used to
generate filesystem paths from track metadata. ComponentValue is imported
from the shared layer so adapters and the domain agree on the structure.
"""

from abc import ABC, abstractmethod
from typing import final, ClassVar, override

from omym.shared.track_metadata import TrackMetadata
from omym.features.path.domain.sanitizer import Sanitizer
from omym.platform.logging import logger
from omym.shared.path_components import ComponentValue


class PathComponent(ABC):
    """Base class for path components."""

    order: int

    def __init__(self, order: int):
        """Initialize the component.

        Args:
            order: Order in which this component appears in the path.
        """
        self.order = order

    @abstractmethod
    def get_value(self, metadata: TrackMetadata) -> ComponentValue:
        """Get the value for this component from metadata.

        Args:
            metadata: Track metadata to extract value from.

        Returns:
            ComponentValue: Component value with metadata.
        """
        pass

    @property
    @abstractmethod
    def component_type(self) -> str:
        """Get the type of this component.

        Returns:
            str: Component type identifier.
        """
        pass


@final
class AlbumArtistComponent(PathComponent):
    """Album artist path component."""

    order: int

    @override
    def get_value(self, metadata: TrackMetadata) -> ComponentValue:
        """Get album artist value from metadata.

        Args:
            metadata: Track metadata to extract value from.

        Returns:
            ComponentValue: Album artist value with metadata.
        """
        # Do not fallback to track artist when album_artist is missing
        album_artist = metadata.album_artist if metadata.album_artist else "Unknown-Artist"

        sanitized = Sanitizer.sanitize_artist_name(album_artist)
        return ComponentValue(value=sanitized, order=self.order, type=self.component_type)

    @property
    @override
    def component_type(self) -> str:
        """Get the component type.

        Returns:
            str: "AlbumArtist"
        """
        return "AlbumArtist"


@final
class AlbumComponent(PathComponent):
    """Album name path component."""

    order: int

    @override
    def get_value(self, metadata: TrackMetadata) -> ComponentValue:
        """Get album value from metadata.

        Args:
            metadata: Track metadata to extract value from.

        Returns:
            ComponentValue: Album value with metadata.
        """
        album = metadata.album if metadata.album else "Unknown-Album"
        sanitized = Sanitizer.sanitize_album_name(album)
        return ComponentValue(value=sanitized, order=self.order, type=self.component_type)

    @property
    @override
    def component_type(self) -> str:
        """Get the component type.

        Returns:
            str: "Album"
        """
        return "Album"


@final
class PathComponentFactory:
    """Factory for creating path components."""

    _components: ClassVar[dict[str, type[PathComponent]]] = {
        "AlbumArtist": AlbumArtistComponent,
        "Album": AlbumComponent,
    }

    @classmethod
    def create(cls, component_type: str, order: int) -> PathComponent | None:
        """Create a path component.

        Args:
            component_type: Type of component to create.
            order: Order in which this component appears in the path.

        Returns:
            PathComponent | None: Created component or None if type is unknown.
        """
        component_class = cls._components.get(component_type)
        if component_class:
            return component_class(order)
        logger.warning(f"Unknown path component type: {component_type}")
        return None

    @classmethod
    def register_component(cls, type_name: str, component_class: type[PathComponent]) -> None:
        """Register a new component type.

        Args:
            type_name: Name of the component type.
            component_class: Component class to register.
        """
        cls._components[type_name] = component_class
