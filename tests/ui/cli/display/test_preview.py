"""Tests for preview display functionality."""

from pathlib import Path
from typing import List

import pytest
from pytest_mock import MockerFixture

from omym.core.metadata.track_metadata import TrackMetadata
from omym.core.metadata.music_file_processor import ProcessResult
from omym.ui.cli.display.preview import PreviewDisplay


@pytest.fixture
def process_results() -> List[ProcessResult]:
    """Create test process results.

    Returns:
        List of test process results.
    """
    metadata = TrackMetadata(
        title="Test Track",
        artist="Artist",
        album="Album",
        genre="Genre",
        year=2024,
        track_number=1,
        track_total=10,
        disc_number=1,
        disc_total=1,
        file_extension=".mp3"
    )
    
    return [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=Path("Artist/Album/01 - Test Track.mp3"),
            success=True,
            metadata=metadata,
            artist_id=None
        )
    ]


def test_show_preview(process_results: List[ProcessResult], mocker: MockerFixture) -> None:
    """Test preview display.

    Args:
        process_results: Test process results fixture.
        mocker: Pytest mocker fixture.
    """
    # Set base path to parent directory of target path
    base_path = Path(".")
    
    # Mock console output
    mock_console = mocker.patch("rich.console.Console")
    mock_instance = mock_console.return_value
    
    # Create display instance
    display = PreviewDisplay()
    display.console = mock_instance
    
    # Show preview
    display.show_preview(process_results, base_path, show_db=True)
    
    # Verify console output was called
    mock_instance.print.assert_called() 