"""Tests for progress display functionality."""

from collections.abc import Generator
from pathlib import Path
import tempfile
import pytest
from pytest_mock import MockerFixture

from typing import Callable
from omym.domain.metadata.track_metadata import TrackMetadata
from omym.domain.metadata.music_file_processor import ProcessResult
from omym.ui.cli.display.progress import ProgressDisplay
from omym.application.services.organize_service import OrganizeRequest


@pytest.fixture
def test_dir() -> Generator[Path, None, None]:
    """Create a temporary test directory with test files.

    Yields:
        Path to test directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create test files
        (temp_path / "test1.mp3").touch()
        (temp_path / "test2.mp3").touch()
        yield temp_path


def test_run_with_service_progress(mocker: MockerFixture) -> None:
    """Test processing via app service with progress display."""
    # Mock Progress
    mock_progress = mocker.patch("omym.ui.cli.display.progress.Progress")
    mock_progress_instance = mock_progress.return_value.__enter__.return_value

    # Create test data
    test_dir = Path("test_music")
    metadata = TrackMetadata(
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        genre="Test Genre",
        year=2024,
        track_number=1,
        track_total=10,
        disc_number=1,
        disc_total=1,
        file_extension=".mp3",
    )
    ok = ProcessResult(
        source_path=Path("test.mp3"),
        target_path=Path("Artist/Album/01 - Test Track.mp3"),
        success=True,
        metadata=metadata,
        artist_id=None,
    )

    # Mock app service that invokes the callback twice and returns two results
    class _App:
        def process_directory_with_progress(
            self,
            request: OrganizeRequest,
            directory: Path,
            progress_callback: Callable[[int, int, Path], None],
        ):
            # Mark parameters as used for type checker
            del request, directory
            progress_callback(1, 2, Path("a.mp3"))
            progress_callback(2, 2, Path("b.mp3"))
            return [ok, ok]

    app = _App()

    # Minimal request object substitute; its fields aren't used in the test
    request = mocker.Mock()

    # Run
    display = ProgressDisplay()
    results = display.run_with_service(app, request, test_dir)

    # Verify progress interactions and results
    mock_progress_instance.add_task.assert_called_once_with("[cyan]Processing files...", total=2)
    assert mock_progress_instance.update.call_count >= 2
    assert len(results) == 2
    assert all(r.success for r in results)


def test_run_with_service_interactive(mocker: MockerFixture) -> None:
    """Test processing via app service in interactive mode."""
    mock_progress = mocker.patch("omym.ui.cli.display.progress.Progress")
    mock_progress_instance = mock_progress.return_value.__enter__.return_value

    test_dir = Path("test_music")

    err = ProcessResult(
        source_path=Path("test.mp3"),
        target_path=None,
        success=False,
        error_message="Test error",
        metadata=None,
        artist_id=None,
    )

    class _App:
        def process_directory_with_progress(
            self,
            request: OrganizeRequest,
            directory: Path,
            progress_callback: Callable[[int, int, Path], None],
        ):
            del request, directory
            progress_callback(1, 2, Path("a.mp3"))
            progress_callback(2, 2, Path("b.mp3"))
            return [err, err]

    app = _App()
    request = mocker.Mock()

    display = ProgressDisplay()
    results = display.run_with_service(app, request, test_dir, interactive=True)

    mock_progress_instance.add_task.assert_called_once_with("[cyan]Processing files...", total=2)
    assert mock_progress_instance.update.call_count >= 2
    assert len(results) == 2
    assert all(not r.success for r in results)
