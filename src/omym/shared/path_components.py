"""Shared path component value objects (domain <-> adapters).

This module centralizes the ComponentValue dataclass so both the path
feature and persistence layers rely on a single definition. That ensures
consistent typing across module boundaries without duplicating logic.
"""

from dataclasses import dataclass


@dataclass
class ComponentValue:
    """Value and metadata describing a single path component."""

    value: str
    order: int
    type: str
