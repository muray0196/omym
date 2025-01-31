"""Tests for path component functionality."""

import pytest
from typing import override

from omym.core.path.path_elements import (
    ComponentValue,
    PathComponent,
    AlbumArtistComponent,
    AlbumComponent,
    PathComponentFactory,
)
from omym.core.metadata.track_metadata import TrackMetadata


@pytest.fixture
def metadata() -> TrackMetadata:
    """Create test metadata.

    Returns:
        TrackMetadata: Test metadata instance.
    """
    return TrackMetadata(
        title="Test Title",
        artist="Test Artist",
        album="Test Album",
        album_artist="Test Album Artist",
        genre="Test Genre",
        year=2024,
        track_number=1,
        track_total=10,
        disc_number=1,
        disc_total=1,
        file_extension=".mp3",
    )


def test_component_value() -> None:
    """Test ComponentValue dataclass."""
    value = ComponentValue(value="test", order=1, type="TestType")
    assert value.value == "test"
    assert value.order == 1
    assert value.type == "TestType"


def test_album_artist_component_with_album_artist(metadata: TrackMetadata) -> None:
    """Test AlbumArtistComponent with album_artist present.

    Args:
        metadata: Test metadata fixture.
    """
    component = AlbumArtistComponent(order=1)
    result = component.get_value(metadata)
    assert result.value == "Test-Album-Artist"
    assert result.order == 1
    assert result.type == "AlbumArtist"


def test_album_artist_component_fallback_to_artist(metadata: TrackMetadata) -> None:
    """Test AlbumArtistComponent falling back to artist.

    Args:
        metadata: Test metadata fixture.
    """
    metadata.album_artist = None
    component = AlbumArtistComponent(order=1)
    result = component.get_value(metadata)
    assert result.value == "Test-Artist"
    assert result.order == 1
    assert result.type == "AlbumArtist"


def test_album_artist_component_unknown(metadata: TrackMetadata) -> None:
    """Test AlbumArtistComponent with no artist info.

    Args:
        metadata: Test metadata fixture.
    """
    metadata.album_artist = None
    metadata.artist = None
    component = AlbumArtistComponent(order=1)
    result = component.get_value(metadata)
    assert result.value == "Unknown-Artist"
    assert result.order == 1
    assert result.type == "AlbumArtist"


def test_album_component_with_album(metadata: TrackMetadata) -> None:
    """Test AlbumComponent with album present.

    Args:
        metadata: Test metadata fixture.
    """
    component = AlbumComponent(order=2)
    result = component.get_value(metadata)
    assert result.value == "Test-Album"
    assert result.order == 2
    assert result.type == "Album"


def test_album_component_unknown(metadata: TrackMetadata) -> None:
    """Test AlbumComponent with no album info.

    Args:
        metadata: Test metadata fixture.
    """
    metadata.album = None
    component = AlbumComponent(order=2)
    result = component.get_value(metadata)
    assert result.value == "Unknown-Album"
    assert result.order == 2
    assert result.type == "Album"


def test_path_component_factory_create_album_artist() -> None:
    """Test PathComponentFactory creating AlbumArtistComponent."""
    component = PathComponentFactory.create("AlbumArtist", 1)
    assert isinstance(component, AlbumArtistComponent)
    assert component.order == 1
    assert component.component_type == "AlbumArtist"


def test_path_component_factory_create_album() -> None:
    """Test PathComponentFactory creating AlbumComponent."""
    component = PathComponentFactory.create("Album", 2)
    assert isinstance(component, AlbumComponent)
    assert component.order == 2
    assert component.component_type == "Album"


def test_path_component_factory_create_unknown() -> None:
    """Test PathComponentFactory with unknown component type."""
    component = PathComponentFactory.create("UnknownType", 1)
    assert component is None


class MockPathComponent(PathComponent):
    """Mock implementation of PathComponent for testing."""

    @override
    def get_value(self, metadata: TrackMetadata) -> ComponentValue:
        """Get test value.

        Args:
            metadata: Track metadata.

        Returns:
            ComponentValue: Test value.
        """
        return ComponentValue(value="test", order=self.order, type=self.component_type)

    @property
    @override
    def component_type(self) -> str:
        """Get component type.

        Returns:
            str: "Test"
        """
        return "Test"


def test_path_component_factory_register_component() -> None:
    """Test registering new component type."""
    # Register new component
    PathComponentFactory.register_component("Test", MockPathComponent)

    # Create component
    component = PathComponentFactory.create("Test", 3)
    assert isinstance(component, MockPathComponent)
    assert component.order == 3
    assert component.component_type == "Test"
