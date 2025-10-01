"""src/omym/ui/cli/commands/preferences.py
What: Implement CLI presentation for artist preference inspection.
Why: Provide a dedicated surface to audit cache versus user overrides.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import final

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from omym.application.services.preferences_service import (
    ArtistPreferenceInspector,
    ArtistPreferenceRow,
)
from omym.platform.db.cache.artist_cache_dao import ArtistCacheDAO
from omym.platform.db.db_manager import DatabaseManager
from omym.ui.cli.args.options import PreferencesArgs


@final
class PreferencesCommand:
    """Render artist name preference state in a Rich table."""

    def __init__(
        self,
        args: PreferencesArgs,
        *,
        db_manager_factory: Callable[[], DatabaseManager] | None = None,
        inspector_factory: Callable[[ArtistCacheDAO], ArtistPreferenceInspector] | None = None,
        console: Console | None = None,
    ) -> None:
        self._args = args
        self._db_manager_factory = db_manager_factory or DatabaseManager
        self._inspector_factory = inspector_factory or self._default_inspector_factory
        self._console = console or Console()

    def execute(self) -> None:
        """Load artist data and print a formatted summary table."""

        manager = self._db_manager_factory()
        with manager as db_manager:
            if db_manager.conn is None:
                self._console.print("[red]Database connection is unavailable.[/red]")
                return

            dao = ArtistCacheDAO(db_manager.conn)
            inspector = self._inspector_factory(dao)
            rows = inspector.collect(include_all=self._args.show_all)

        if not rows:
            if self._args.only_missing:
                self._console.print("[yellow]No missing artist preferences detected.[/yellow]")
            else:
                self._console.print("[yellow]No artist preference data available.[/yellow]")
            return

        table = self._build_table(rows)
        self._console.print(table)

    def _default_inspector_factory(self, dao: ArtistCacheDAO) -> ArtistPreferenceInspector:
        return ArtistPreferenceInspector(dao)

    def _build_table(self, rows: list[ArtistPreferenceRow]) -> Table:
        table = Table(
            title="Artist Preference Overview",
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE_HEAD,
            highlight=True,
        )
        table.add_column("Artist", style="bold")
        table.add_column("Preferred")
        table.add_column("Cached")
        table.add_column("Source", style="dim")
        table.add_column("Status")

        for row in rows:
            preferred_cell = self._format_preferred(row)
            cached_cell = self._format_cached(row)
            source_cell = self._format_source(row)
            status_cell = self._format_status(row)
            table.add_row(row.artist_name, preferred_cell, cached_cell, source_cell, status_cell)

        return table

    @staticmethod
    def _format_preferred(row: ArtistPreferenceRow) -> Text:
        if row.preferred_name is None:
            return Text("N/A", style="dim")
        if row.cached_name == row.preferred_name:
            return Text(row.preferred_name, style="green")
        return Text(row.preferred_name, style="bold cyan")

    @staticmethod
    def _format_cached(row: ArtistPreferenceRow) -> Text:
        if row.cached_name is None:
            return Text("N/A", style="dim")
        if row.preferred_name == row.cached_name and row.preferred_name is not None:
            return Text(row.cached_name, style="green")
        return Text(row.cached_name, style="yellow")

    @staticmethod
    def _format_source(row: ArtistPreferenceRow) -> Text:
        if row.source is None:
            return Text("N/A", style="dim")
        return Text(row.source, style="dim")

    @staticmethod
    def _format_status(row: ArtistPreferenceRow) -> Text:
        if row.preferred_name is None and row.cached_name is None:
            return Text("untracked", style="yellow")
        if row.preferred_name is None:
            return Text("needs preference", style="yellow")
        if row.cached_name is None:
            return Text("missing cache", style="red")
        if row.preferred_name != row.cached_name:
            return Text("override", style="cyan")
        return Text("synced", style="green")
