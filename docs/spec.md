owner: Maintainers
status: draft
last_updated: 2025-09-03
review_cadence: quarterly

## Goals and Success Metrics
- Provide a deterministic folder structure for local music libraries.
- Success is measured by correctly processing supported files without data loss.

## In-scope / Out-of-scope
- In-scope: scanning directories, reading metadata, moving and renaming files, and caching results in SQLite. Lyrics (.lrc) files that share a stem with supported audio are moved and renamed alongside their tracks. Artwork (.jpg/.png) stored with supported audio travels with the directory's primary track without renaming.
- Out-of-scope: editing tags, network operations, or streaming media.

## User Stories and Acceptance Criteria
- As a music collector, I can run `omym <source> <target>` and files are organized into `<target>/<Artist>/<Album>/` directories when tags are present.
- As a user, filenames are sanitized so the library is portable across operating systems.

## Flows
- Primary: CLI invocation → configuration loading → metadata extraction → path generation → file operations → database update.
- Restore: CLI invocation → configuration loading → restoration plan build from SQLite → collision handling → file moves (audio + lyrics/artwork) → optional database purge.
- Error paths: missing tags or DB errors are logged and the affected files are skipped.
- The tool runs synchronously with no built-in retry logic beyond the current process.

## Non-functional Requirements
- Processes thousands of files on a modern laptop without exhausting memory.
- Operates completely offline and stores data locally.
- Logging follows PEP 282 conventions.

## Assumptions, Constraints, Dependencies
- Requires Python ≥3.13 and dependencies defined in `pyproject.toml`.
- Files reside on a local filesystem and the database is SQLite.
- Single-process execution; no concurrency is implemented.

## Test Ideas / Examples
- Run `uv run pytest` to validate metadata parsing, path generation, and database operations.
- Add fixtures where artwork assets accompany tracks to confirm images relocate during organization.
- Simulate unsupported formats or missing tags to verify error handling.
