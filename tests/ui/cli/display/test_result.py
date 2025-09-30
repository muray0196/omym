"""Tests for result display functionality."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from omym.features.metadata import ProcessResult, TrackMetadata
from omym.ui.cli.display.result import ResultDisplay


@pytest.fixture
def process_results() -> list[ProcessResult]:
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


def test_show_results(process_results: list[ProcessResult], mocker: MockerFixture) -> None:
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


def test_show_results_quiet(process_results: list[ProcessResult], mocker: MockerFixture) -> None:
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


def test_show_results_success(mocker: MockerFixture) -> None:
    """Test showing successful results."""
    # Mock console
    mock_console = mocker.patch("omym.ui.cli.display.result.Console")
    display = ResultDisplay()

    # Create test results
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

    results = [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=Path("Artist/Album/01 - Test Track.mp3"),
            success=True,
            metadata=metadata,
            artist_id=None,
        ),
        ProcessResult(
            source_path=Path("test2.mp3"),
            target_path=Path("Artist/Album/02 - Test Track.mp3"),
            success=True,
            metadata=metadata,
            artist_id=None,
        ),
    ]

    # Show results
    display.show_results(results)

    # Verify console output
    mock_console.return_value.print.assert_any_call("\n[bold]Processing Summary:[/bold]")
    mock_console.return_value.print.assert_any_call("Total files processed: 2")
    mock_console.return_value.print.assert_any_call("[green]Successful: 2[/green]")


def test_show_results_with_failures(mocker: MockerFixture) -> None:
    """Test showing results with failures."""
    # Mock console
    mock_console = mocker.patch("omym.ui.cli.display.result.Console")
    display = ResultDisplay()

    # Create test results
    results = [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=None,
            success=False,
            error_message="Test error 1",
            metadata=None,
            artist_id=None,
        ),
        ProcessResult(
            source_path=Path("test2.mp3"),
            target_path=None,
            success=False,
            error_message="Test error 2",
            metadata=None,
            artist_id=None,
        ),
    ]

    # Show results
    display.show_results(results)

    # Verify console output
    mock_console.return_value.print.assert_any_call("\n[bold]Processing Summary:[/bold]")
    mock_console.return_value.print.assert_any_call("Total files processed: 2")
    mock_console.return_value.print.assert_any_call("[green]Successful: 0[/green]")
    mock_console.return_value.print.assert_any_call("[red]Failed: 2[/red]")
    mock_console.return_value.print.assert_any_call("[red]  • test1.mp3: Test error 1[/red]")
    mock_console.return_value.print.assert_any_call("[red]  • test2.mp3: Test error 2[/red]")


def test_result_summary_uses_helper(mocker: MockerFixture) -> None:
    """Ensure result display delegates to the shared helper with live labels."""
    mock_console = mocker.patch("omym.ui.cli.display.result.Console")
    render_mock = mocker.patch("omym.ui.cli.display.result.render_processing_summary")
    display = ResultDisplay()
    results: list[ProcessResult] = []

    display.show_results(results)

    render_mock.assert_called_once_with(
        console=mock_console.return_value,
        results=results,
        header_label="Processing Summary",
        total_label="Total files processed",
        success_label="Successful",
        failure_label="Failed",
    )


def test_show_results_quiet_mode(mocker: MockerFixture) -> None:
    """Test showing results in quiet mode."""
    mock_console = mocker.patch("omym.ui.cli.display.result.Console")
    render_mock = mocker.patch("omym.ui.cli.display.result.render_processing_summary")
    display = ResultDisplay()

    results = [
        ProcessResult(
            source_path=Path("test.mp3"),
            target_path=None,
            success=False,
            error_message="Test error",
            metadata=None,
            artist_id=None,
        ),
    ]

    display.show_results(results, quiet=True)

    mock_console.return_value.print.assert_not_called()
    render_mock.assert_not_called()


def test_show_unprocessed_total_counts_files(mocker: MockerFixture) -> None:
    """Ensure unprocessed total rendering includes the provided count."""

    mock_console = mocker.patch("omym.ui.cli.display.result.Console")
    display = ResultDisplay()

    display.show_unprocessed_total(2, quiet=False)

    mock_console.return_value.print.assert_called_with(
        "Unprocessed files awaiting review: 2"
    )


def test_show_unprocessed_total_respects_quiet(mocker: MockerFixture) -> None:
    """Ensure quiet mode suppresses the unprocessed count output."""

    mock_console = mocker.patch("omym.ui.cli.display.result.Console")
    display = ResultDisplay()

    display.show_unprocessed_total(5, quiet=True)

    mock_console.return_value.print.assert_not_called()
