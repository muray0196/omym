owner: Maintainers
status: active
last_updated: 2025-09-17
review_cadence: quarterly

- **Artist Romanisation**: Process of converting non-Latin artist names into Latin script using cached MusicBrainz aliases.
- **Collision Policy**: Strategy applied during restore when a destination path already exists (`abort`, `skip`, or `backup`).
- **ProcessResult**: Domain object describing the outcome of organising a single file, including target path, metadata, and warnings.
- **ProcessingEvent**: Structured log identifier (e.g., `processing.file.success`) emitted by the organiser for machine-readable telemetry.
- **Restore Plan**: Ordered set of file operations derived from SQLite state that the restoration service executes.
- **Thread Pool**: Bounded `ThreadPoolExecutor` used by `MusicProcessor` to parallelise hashing and metadata IO while keeping memory usage predictable.
- **Dry Run**: Execution mode that performs planning, hashing, and logging without mutating the filesystem.
