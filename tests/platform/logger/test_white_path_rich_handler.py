"""Tests for the ``WhitePathRichHandler`` path formatting utilities."""

from __future__ import annotations

import logging
from io import StringIO
from typing import Any

from rich.console import Console
from rich.text import Text

from omym.platform.logging import WhitePathRichHandler


def _make_handler() -> WhitePathRichHandler:
    """Create a handler instance with an in-memory console."""

    console = Console(file=StringIO(), force_terminal=True, soft_wrap=True)
    return WhitePathRichHandler(console=console)


def _build_record(**extras: Any) -> logging.LogRecord:
    """Create a ``LogRecord`` populated with processing extras for testing."""

    record = logging.LogRecord(
        name="omym",
        level=logging.INFO,
        pathname="test",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    )
    for key, value in extras.items():
        setattr(record, key, value)
    return record


def test_render_message_truncates_long_absolute_paths() -> None:
    """Absolute source paths should be abbreviated with an ellipsis prefix."""

    handler = _make_handler()
    source_path = "/home/hwmch/music/music_test/Various-Artists/2019_A-Dance-of-Fire-and-Ice-OST/D1_13_One-forgotten-night_QUREE.flac"

    record = _build_record(
        processing_event="processing.file.success",
        sequence=3,
        total_files=13,
        source_path=source_path,
        duration_ms=27.69,
        artist="Quree",
        title="One forgotten night",
    )

    rendered = handler.render_message(record, "")
    assert isinstance(rendered, Text)

    plain = rendered.plain
    assert "…/music_test/Various-Artists/2019_A-Dance-of-Fire-and-Ice-OST/D1_13_One-forgotten-night_QUREE.flac" in plain


def test_render_message_relativizes_paths_to_base_directory() -> None:
    """Source paths beneath the base directory should render as relative segments."""

    handler = _make_handler()
    base = "/home/hwmch/music/music_test"
    source_path = f"{base}/KAF/2025_花譜-歌ってみた-vol-6/D1_134_hp_KAF.opus"

    record = _build_record(
        processing_event="processing.file.success",
        sequence=9,
        total_files=13,
        source_path=source_path,
        source_base_path=base,
        target_path=f"{base}/Library/KAF/2025/D1_134_hp_KAF.opus",
        target_base_path=base,
        duration_ms=5.98,
        artist="KAF",
        title="hp",
    )

    rendered = handler.render_message(record, "")
    assert isinstance(rendered, Text)

    plain = rendered.plain
    assert "KAF/2025_花譜-歌ってみた-vol-6/D1_134_hp_KAF.opus" in plain
    assert "/home/hwmch/music" not in plain


def test_render_message_handles_windows_paths() -> None:
    """Windows-style paths should retain backslash separators when relativized."""

    handler = _make_handler()
    base = "C\\media\\incoming"
    source_path = "C\\media\\incoming\\Artist\\Album\\Disc\\Track.flac"

    record = _build_record(
        processing_event="processing.file.move",
        sequence=1,
        total_files=5,
        source_path=source_path,
        source_base_path=base,
        target_path="D:\\archive\\Artist\\Album\\Disc\\Track.flac",
        target_base_path="D:\\archive",
    )

    rendered = handler.render_message(record, "")
    assert isinstance(rendered, Text)

    plain = rendered.plain
    assert "Artist\\Album\\Disc\\Track.flac" in plain
    assert "C:\\media" not in plain
