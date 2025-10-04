"""
Summary: SQLite-backed filter registry adapter implementing the organization port.
Why: Encapsulate FilterDAO interactions so the use case stays persistence agnostic.
"""

from __future__ import annotations

from typing import final

from omym.platform.db.daos.filter_dao import FilterDAO

from ..usecases.ports import FilterHierarchyRecord, FilterRegistryPort


@final
class FilterDaoAdapter(FilterRegistryPort):
    """Adapter exposing ``FilterDAO`` through the filter registry port."""

    def __init__(self, dao: FilterDAO) -> None:
        """Store the DAO dependency."""
        self._dao = dao

    def insert_hierarchy(self, name: str, priority: int) -> int | None:
        return self._dao.insert_hierarchy(name, priority)

    def get_hierarchies(self) -> list[FilterHierarchyRecord]:
        return [
            FilterHierarchyRecord(id=item.id, name=item.name, priority=item.priority)
            for item in self._dao.get_hierarchies()
        ]

    def insert_value(self, hierarchy_id: int, file_hash: str, value: str) -> bool:
        return self._dao.insert_value(hierarchy_id, file_hash, value)
