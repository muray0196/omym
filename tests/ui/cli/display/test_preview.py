"""Tests for preview display functionality."""

from pathlib import Path
from pytest_mock import MockerFixture

from omym.core.metadata.track_metadata import TrackMetadata
from omym.core.metadata.music_file_processor import ProcessResult
from omym.ui.cli.display.preview import PreviewDisplay


def test_show_preview_basic(mocker: MockerFixture) -> None:
    """Test showing basic preview."""
    # Mock console
    mock_console = mocker.patch("omym.ui.cli.display.preview.Console")
    display = PreviewDisplay()

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

    base_path = Path("base/path")
    results = [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=base_path / "Artist/Album/01 - Test Track.mp3",
            success=True,
            metadata=metadata,
            artist_id=None,
        ),
    ]

    # Show preview
    display.show_preview(results, base_path)

    # Verify console output
    mock_console.return_value.print.assert_any_call("\n[bold cyan]Preview of planned changes:[/bold cyan]")
    mock_console.return_value.print.assert_any_call("\n[bold]Summary:[/bold]")
    mock_console.return_value.print.assert_any_call("Total files to process: 1")
    mock_console.return_value.print.assert_any_call("[green]Will succeed: 1[/green]")


def test_show_preview_with_db(mocker: MockerFixture) -> None:
    """Test showing preview with database operations."""
    # Mock console
    mock_console = mocker.patch("omym.ui.cli.display.preview.Console")
    display = PreviewDisplay()

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

    base_path = Path("base/path")
    results = [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=base_path / "Artist/Album/01 - Test Track.mp3",
            success=True,
            metadata=metadata,
            artist_id="TEST1",
            file_hash="hash1",
        ),
    ]

    # Show preview with DB operations
    display.show_preview(results, base_path, show_db=True)

    # Verify console output
    mock_console.return_value.print.assert_any_call("\n[bold cyan]Preview of planned changes:[/bold cyan]")
    mock_console.return_value.print.assert_any_call("\n[bold magenta]Database Operations Preview:[/bold magenta]")
    mock_console.return_value.print.assert_any_call("\n[bold]Summary:[/bold]")
    mock_console.return_value.print.assert_any_call("Total files to process: 1")
    mock_console.return_value.print.assert_any_call("[green]Will succeed: 1[/green]")


def test_show_preview_with_errors(mocker: MockerFixture) -> None:
    """Test showing preview with errors."""
    # Mock console
    mock_console = mocker.patch("omym.ui.cli.display.preview.Console")
    display = PreviewDisplay()

    # Create test results
    results = [
        ProcessResult(
            source_path=Path("test1.mp3"),
            target_path=None,
            success=False,
            error_message="Test error",
            metadata=None,
            artist_id=None,
        ),
    ]

    # Show preview
    display.show_preview(results, Path("base/path"))

    # Verify console output
    mock_console.return_value.print.assert_any_call("\n[bold cyan]Preview of planned changes:[/bold cyan]")
    mock_console.return_value.print.assert_any_call("\n[bold]Summary:[/bold]")
    mock_console.return_value.print.assert_any_call("Total files to process: 1")
    mock_console.return_value.print.assert_any_call("[green]Will succeed: 0[/green]")
    mock_console.return_value.print.assert_any_call("[red]Will fail: 1[/red]")
    mock_console.return_value.print.assert_any_call("[red]  • test1.mp3: Test error[/red]")
