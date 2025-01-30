"""Tests for result display functionality."""

from pathlib import Path
from typing import List

import pytest
from pytest_mock import MockerFixture

from omym.core.metadata.music_file_processor import ProcessResult
from omym.ui.cli.display.result import ResultDisplay


@pytest.fixture
def process_results() -> List[ProcessResult]:
    """Create test process results.

    Returns:
        List of test process results.
    """
    return [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=Path("output/test1.mp3"),
            success=True,
        ),
        ProcessResult(
            source_path=Path("test2.mp3"),
            target_path=Path("output/test2.mp3"),
            success=False,
            error_message="Test error",
        ),
    ]


def test_show_results(process_results: List[ProcessResult], mocker: MockerFixture) -> None:
    """Test result display.

    Args:
        process_results: Test process results fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock console output
    mock_console = mocker.patch("rich.console.Console")
    mock_instance = mock_console.return_value

    # Create display instance
    display = ResultDisplay()
    display.console = mock_instance

    # Show results
    display.show_results(process_results, quiet=False)

    # Verify console output
    assert mock_instance.print.call_count > 0  # Multiple print calls expected


def test_show_results_quiet(process_results: List[ProcessResult], mocker: MockerFixture) -> None:
    """Test result display in quiet mode.

    Args:
        process_results: Test process results fixture.
        mocker: Pytest mocker fixture.
    """
    # Mock console output
    mock_console = mocker.patch("rich.console.Console")
    mock_instance = mock_console.return_value

    # Create display instance
    display = ResultDisplay()
    display.console = mock_instance

    # Show results in quiet mode
    display.show_results(process_results, quiet=True)

    # Verify no console output
    mock_instance.print.assert_not_called() 