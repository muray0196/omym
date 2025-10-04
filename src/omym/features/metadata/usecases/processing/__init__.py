"""
Summary: Expose metadata processing entry points from the consolidated package.
Why: Keep callers stable while reorganising helpers under processing/ submodules.
"""

from .cleanup import (
    calculate_pending_unprocessed,
    relocate_unprocessed_files,
    snapshot_unprocessed_candidates,
)
from .directory_runner import run_directory_processing
from .file_operations import (
    calculate_file_hash,
    find_available_path,
    generate_target_path,
    move_file,
)
from .file_runner import run_file_processing
from .processing_types import (
    ArtworkProcessingResult,
    DirectoryRollbackError,
    LyricsProcessingResult,
    ProcessResult,
    ProcessingEvent,
    ProcessingLogContext,
)

__all__ = [
    "run_file_processing",
    "run_directory_processing",
    "ProcessResult",
    "ProcessingEvent",
    "ProcessingLogContext",
    "DirectoryRollbackError",
    "LyricsProcessingResult",
    "ArtworkProcessingResult",
    "calculate_file_hash",
    "find_available_path",
    "generate_target_path",
    "move_file",
    "snapshot_unprocessed_candidates",
    "relocate_unprocessed_files",
    "calculate_pending_unprocessed",
]
