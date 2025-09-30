"""tests/ui/cli/display/test_preview.py
Where: CLI preview display tests.
What: Validate tree rendering for process preview scenarios.
Why: Guard against regressions in user-facing status cues.
"""

from pathlib import Path
from typing import ClassVar
from pytest_mock import MockerFixture

from omym.features.metadata import TrackMetadata
from omym.features.metadata import (
    ArtworkProcessingResult,
    LyricsProcessingResult,
    ProcessResult,
)
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


def test_show_preview_includes_lyrics(mocker: MockerFixture) -> None:
    """Lyrics files appear in the preview alongside their tracks."""

    _ = mocker.patch("omym.ui.cli.display.preview.Console")

    class FakeNode:
        def __init__(self, label: str) -> None:
            self.label: str = label
            self.children: list["FakeNode"] = []

        def add(self, label: str) -> "FakeNode":
            child = FakeNode(label)
            self.children.append(child)
            return child

    class FakeTree(FakeNode):
        last_instance: ClassVar["FakeTree | None"] = None

        def __init__(self, label: str) -> None:
            super().__init__(label)
            FakeTree.last_instance = self

    _ = mocker.patch("omym.ui.cli.display.preview.Tree", FakeTree)

    display = PreviewDisplay()
    base_path = Path("library")
    audio_target = base_path / "Artist/Album/01_track.mp3"
    lyrics_target = audio_target.with_suffix(".lrc")

    result = ProcessResult(
        source_path=Path("01_track.mp3"),
        target_path=audio_target,
        success=True,
        dry_run=True,
        lyrics_result=LyricsProcessingResult(
            source_path=Path("01_track.lrc"),
            target_path=lyrics_target,
            moved=False,
            dry_run=True,
        ),
    )

    display.show_preview([result], base_path)

    tree = FakeTree.last_instance
    assert tree is not None
    assert tree.children, "Artist node should be present in preview"

    artist_node = tree.children[0]
    assert artist_node.children, "Album node should be present in preview"

    album_node = artist_node.children[0]
    leaf_labels = [child.label for child in album_node.children]
    assert any(label.startswith("🎵") and label.endswith(".mp3 [yellow]Preview[/yellow]") for label in leaf_labels)
    assert any(label.startswith("📝") and label.endswith(".lrc [yellow]Preview[/yellow]") for label in leaf_labels)


def test_show_preview_includes_artwork(mocker: MockerFixture) -> None:
    """Artwork entries include move, skip, and dry-run statuses."""

    _ = mocker.patch("omym.ui.cli.display.preview.Console")

    class FakeNode:
        def __init__(self, label: str) -> None:
            self.label: str = label
            self.children: list["FakeNode"] = []

        def add(self, label: str) -> "FakeNode":
            child = FakeNode(label)
            self.children.append(child)
            return child

    class FakeTree(FakeNode):
        last_instance: ClassVar["FakeTree | None"] = None

        def __init__(self, label: str) -> None:
            super().__init__(label)
            FakeTree.last_instance = self

    _ = mocker.patch("omym.ui.cli.display.preview.Tree", FakeTree)

    display = PreviewDisplay()
    base_path = Path("library")
    audio_target = base_path / "Artist/Album/01_track.mp3"
    artwork_target = audio_target.with_name("cover.jpg")

    result = ProcessResult(
        source_path=Path("01_track.mp3"),
        target_path=audio_target,
        success=True,
        artwork_results=[
            ArtworkProcessingResult(
                source_path=Path("cover.jpg"),
                target_path=artwork_target,
                linked_track=audio_target,
                moved=True,
                dry_run=False,
            ),
            ArtworkProcessingResult(
                source_path=Path("duplicate_cover.jpg"),
                target_path=artwork_target,
                linked_track=audio_target,
                moved=False,
                dry_run=False,
                reason="target_exists",
            ),
            ArtworkProcessingResult(
                source_path=Path("cover_dry_run.jpg"),
                target_path=audio_target.with_name("cover_dry_run.jpg"),
                linked_track=audio_target,
                moved=False,
                dry_run=True,
            ),
        ],
    )

    display.show_preview([result], base_path)

    tree = FakeTree.last_instance
    assert tree is not None
    assert tree.children, "Artist node should be present in preview"

    artist_node = tree.children[0]
    assert artist_node.children, "Album node should be present in preview"

    album_node = artist_node.children[0]
    artwork_labels = [label for label in (child.label for child in album_node.children) if label.startswith("🖼️")]

    assert any("✅" in label and "[green]Done[/green]" in label for label in artwork_labels)
    assert any("⚠️" in label and "Skipped (target already exists)" in label for label in artwork_labels)
    assert any("✨" in label and label.endswith("[yellow]Preview[/yellow]") for label in artwork_labels)


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


def test_preview_summary_uses_helper(mocker: MockerFixture) -> None:
    """Ensure preview summary delegates to the shared helper."""
    mock_console = mocker.patch("omym.ui.cli.display.preview.Console")
    render_mock = mocker.patch("omym.ui.cli.display.preview.render_processing_summary")
    display = PreviewDisplay()
    results: list[ProcessResult] = []

    display.show_preview(results, Path("library"))

    render_mock.assert_called_once_with(
        console=mock_console.return_value,
        results=results,
        header_label="Summary",
        total_label="Total files to process",
        success_label="Will succeed",
        failure_label="Will fail",
    )
