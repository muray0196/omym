"""Smoke tests for unified entry points.

These tests assert that `python -m omym` and the console script
both resolve to the CLI's `main` function exposed under `omym.ui.cli`.
"""

from importlib import import_module


def test_module_entry_point_exposes_main() -> None:
    """`python -m omym` path exposes a `main` callable."""
    m = import_module("omym.__main__")
    assert hasattr(m, "main")


def test_console_script_target_exposes_main() -> None:
    """Console script points to `omym.ui.cli:main` and is importable."""
    m = import_module("omym.ui.cli")
    assert hasattr(m, "main")
