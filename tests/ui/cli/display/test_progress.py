"""Tests for progress display functionality."""

from pathlib import Path
import tempfile
from typing import Generator
from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture

from omym.core.metadata.music_file_processor import MusicProcessor
from omym.ui.cli.display.progress import ProgressDisplay


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


def test_process_files_with_progress(
    test_dir: Path,
    mocker: MockerFixture,
) -> None:
    """Test file processing with progress display.

    Args:
        test_dir: Test directory fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock processor
    mock_processor = mocker.Mock(spec=MusicProcessor)
    mock_processor.process_file.return_value.success = True
    
    # Create progress mock with context manager
    mock_progress = MagicMock()
    mock_task = MagicMock()
    mock_progress.add_task.return_value = mock_task
    
    # Create context manager mock
    context_manager = MagicMock()
    context_manager.__enter__.return_value = mock_progress
    context_manager.__exit__.return_value = None
    
    # Patch Progress at the correct import path with autospec
    mocker.patch(
        "omym.ui.cli.display.progress.Progress",
        return_value=context_manager,
        autospec=True
    )
    
    # Create display instance
    display = ProgressDisplay()
    
    # Process files
    results = display.process_files_with_progress(
        mock_processor,
        test_dir,
        interactive=False,
    )
    
    # Verify
    assert len(results) == 2  # Two test files
    mock_processor.process_file.assert_called()
    mock_progress.add_task.assert_called_once_with(
        "[cyan]Processing files...",
        total=2
    )
    # Verify progress updates
    mock_progress.update.assert_called() 