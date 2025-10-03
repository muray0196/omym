"""
/*
Path: tests/features/metadata/usecases/test_package_layout.py
Summary: Verifies reorganised metadata use case package exports.
Why: Guard against regressions when modules move between subpackages.
*/
"""

"""Ensure reorganised metadata use case packages remain importable."""

from importlib import import_module


def test_processing_subpackage_exposes_flow_modules() -> None:
    """Processing package should expose orchestration helpers via __all__."""

    processing = import_module("omym.features.metadata.usecases.processing")

    assert hasattr(processing, "directory_runner")
    assert hasattr(processing, "file_runner")
    assert hasattr(processing, "music_file_processor")
    assert hasattr(processing, "processing_types")


def test_assets_subpackage_exposes_helpers() -> None:
    """Assets package should re-export detection and logging helpers."""

    assets = import_module("omym.features.metadata.usecases.assets")

    assert hasattr(assets, "asset_detection")
    assert hasattr(assets, "asset_logging")
    assert hasattr(assets, "artwork_assets")
    assert hasattr(assets, "lyrics_assets")
    assert hasattr(assets, "associated_assets")


def test_file_management_subpackage_exposes_utilities() -> None:
    """File management package should surface filesystem helper modules."""

    file_management = import_module("omym.features.metadata.usecases.file_management")

    assert hasattr(file_management, "file_context")
    assert hasattr(file_management, "file_duplicate")
    assert hasattr(file_management, "file_operations")
    assert hasattr(file_management, "file_success")


def test_cleanup_subpackage_exposes_cleanup_helpers() -> None:
    """Cleanup package should expose lifecycle utilities."""

    cleanup = import_module("omym.features.metadata.usecases.cleanup")

    assert hasattr(cleanup, "unprocessed_cleanup")
