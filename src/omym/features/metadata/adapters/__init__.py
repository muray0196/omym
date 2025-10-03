"""src/omym/features/metadata/adapters/__init__.py
What: Package marker for metadata adapters.
Why: Allow adapter modules to live alongside use cases with a clear namespace."""

from .filesystem_adapter import LocalFilesystemAdapter

__all__ = ["LocalFilesystemAdapter"]
