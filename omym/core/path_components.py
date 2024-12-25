"""Path component handling functionality."""

from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass

from omym.core.metadata import TrackMetadata
from omym.core.sanitizer import Sanitizer
from omym.utils.logger import logger


@dataclass
class ComponentValue:
    """Value and metadata for a path component."""

    value: str
    order: int
    type: str


class PathComponent(ABC):
    """Base class for path components."""

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


class AlbumArtistComponent(PathComponent):
    """Album artist path component."""

    def get_value(self, metadata: TrackMetadata) -> ComponentValue:
        """Get album artist value from metadata.

        Args:
            metadata: Track metadata to extract value from.

        Returns:
            ComponentValue: Album artist value with metadata.
        """
        album_artist = (
            metadata.album_artist if metadata.album_artist else metadata.artist
        )
        if not album_artist:
            album_artist = "Unknown-Artist"

        sanitized = Sanitizer.sanitize_artist_name(album_artist)
        return ComponentValue(
            value=sanitized, order=self.order, type=self.component_type
        )

    @property
    def component_type(self) -> str:
        """Get the component type.

        Returns:
            str: "AlbumArtist"
        """
        return "AlbumArtist"


class AlbumComponent(PathComponent):
    """Album name path component."""

    def get_value(self, metadata: TrackMetadata) -> ComponentValue:
        """Get album value from metadata.

        Args:
            metadata: Track metadata to extract value from.

        Returns:
            ComponentValue: Album value with metadata.
        """
        album = metadata.album if metadata.album else "Unknown-Album"
        sanitized = Sanitizer.sanitize_album_name(album)
        return ComponentValue(
            value=sanitized, order=self.order, type=self.component_type
        )

    @property
    def component_type(self) -> str:
        """Get the component type.

        Returns:
            str: "Album"
        """
        return "Album"


class PathComponentFactory:
    """Factory for creating path components."""

    _components: Dict[str, type[PathComponent]] = {
        "AlbumArtist": AlbumArtistComponent,
        "Album": AlbumComponent,
    }

    @classmethod
    def create(cls, component_type: str, order: int) -> Optional[PathComponent]:
        """Create a path component.

        Args:
            component_type: Type of component to create.
            order: Order in which this component appears in the path.

        Returns:
            Optional[PathComponent]: Created component or None if type is unknown.
        """
        component_class = cls._components.get(component_type)
        if component_class:
            return component_class(order)
        logger.warning(f"Unknown path component type: {component_type}")
        return None

    @classmethod
    def register_component(
        cls, type_name: str, component_class: type[PathComponent]
    ) -> None:
        """Register a new component type.

        Args:
            type_name: Name of the component type.
            component_class: Component class to register.
        """
        cls._components[type_name] = component_class
