"""Restore command implementation for the CLI."""

from __future__ import annotations

from typing import final

from omym.application.services.restore_service import RestoreMusicService, RestoreServiceRequest
from omym.features.restoration.domain.models import RestoreResult
from omym.ui.cli.args.options import RestoreArgs
from omym.ui.cli.display.restore_result import RestoreResultDisplay


@final
class RestoreCommand:
    """Command that orchestrates database-driven restoration."""

    def __init__(self, args: RestoreArgs) -> None:
        self.args = args
        self.service = RestoreMusicService()
        self.display = RestoreResultDisplay()

    def execute(self) -> list[RestoreResult]:
        """Execute the restore command."""

        request = RestoreServiceRequest(
            source_root=self.args.source_root,
            destination_root=self.args.destination_root,
            dry_run=self.args.dry_run,
            collision_policy=self.args.collision_policy,
            backup_suffix=self.args.backup_suffix,
            continue_on_error=self.args.continue_on_error,
            limit=self.args.limit,
            purge_state=self.args.purge_state,
        )
        results = self.service.run(request)
        self.display.show_results(results, quiet=self.args.quiet)
        return results
