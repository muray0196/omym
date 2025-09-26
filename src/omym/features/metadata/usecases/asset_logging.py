"""src/omym/features/metadata/usecases/asset_logging.py
What: Shared protocol definition for structured processing log callbacks.
Why: Allow asset helpers to depend on a minimal logging contract.
"""

from __future__ import annotations

from typing import Protocol

from .processing_types import ProcessingEvent


class ProcessLogger(Protocol):
    """Signature for structured processing log emitters."""

    def __call__(
        self,
        level: int,
        event: ProcessingEvent,
        message: str,
        *message_args: object,
        **context: object,
    ) -> None:
        ...


__all__ = ["ProcessLogger"]
