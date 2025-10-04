"""tests/features/metadata/test_package_exports.py
What: Validate metadata usecase packages expose expected helpers.
Why: Prevent regressions when reorganising assets and processing modules.
"""

from importlib import import_module


def test_assets_package_exports() -> None:
    """Assets package should expose helpers relied upon by callers."""

    assets = import_module("omym.features.metadata.usecases.assets")

    expected_names = {
        "ProcessLogger",
        "find_associated_lyrics",
        "resolve_directory_artwork",
        "process_lyrics",
        "process_artwork",
        "summarize_lyrics",
        "summarize_artwork",
    }

    for name in expected_names:
        assert hasattr(assets, name), f"Missing export: {name}"


def test_processing_package_exports() -> None:
    """Processing package should re-export orchestration entry points."""

    processing = import_module("omym.features.metadata.usecases.processing")

    expected_names = {
        "run_file_processing",
        "run_directory_processing",
        "ProcessResult",
        "ProcessingEvent",
        "snapshot_unprocessed_candidates",
        "relocate_unprocessed_files",
        "calculate_pending_unprocessed",
    }

    for name in expected_names:
        assert hasattr(processing, name), f"Missing export: {name}"
