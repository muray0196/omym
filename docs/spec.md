owner: Maintainers
status: active
last_updated: 2024-10-17
review_cadence: quarterly

## Goals and Success Metrics
- Deliver a deterministic folder structure for supported audio formats by normalising metadata and filenames.
- Preserve user content: no destructive writes and reversible operations for 100% of files that enter the organiser.
- Reach >99% success rate for processing supported files in internal regression suites and surface actionable errors for the remainder.
- Restore operations complete with zero data loss when run with the default `--collision-policy abort` guardrail.

## In-scope / Out-of-scope
- **In-scope**: scanning directories, extracting and enriching tags, hashing files, grouping into disc/track hierarchies, relocating audio, `.lrc` lyrics, and companion artwork, persisting processing state in SQLite, and restoring files back to their recorded origins. Command options include dry-run previews, cache maintenance, and collision policy selection.
- **Out-of-scope**: mutating embedded tags, downloading remote assets, streaming playback, concurrent multi-host coordination, or automating configuration management beyond the local machine.

## User Stories and Acceptance Criteria
- **Organise an entire library**: Given `uv run python -m omym organize <source> --target <dest>`, all supported tracks move under `<dest>/<Artist>/<YYYY_Album>/` using sanitised directory and file names, and the command exits with status 0 when no failures are reported.
- **Preview without side effects**: When `--dry-run` is supplied, no filesystem changes occur, the console lists the plan, and the SQLite log persists the preview for later inspection.
- **Preview duplicates clearly**: Dry-run previews label detected duplicate hashes as `Skipped (duplicate)` and in-place matches as `Skipped (already organized)` so operators can triage no-op entries before executing real moves.
- **Cache preview IDs**: Database previews surface cached artist IDs when available and rely on filename heuristics only when results omit an ID.
- **Handle multi-disc releases**: Tracks containing disc metadata are written as `<dest>/<Artist>/<YYYY_Album>/D<n>_<track>_<title>_<artistId>.<ext>` (adding the disc prefix only when required), and duplicate hashes are skipped with a warning rather than overwriting existing files.
- **Restore previous runs**: Running `uv run python -m omym restore <dest>` replays the persisted plan back to the original paths (or an alternate `--destination`) honouring the selected collision policy (`abort`, `skip`, or `backup`), and automatically moves any files parked under `<dest>/<unprocessed_dir_name>/` back to their relative paths.
- **Maintain caches**: Supplying `--clear-cache` clears persisted processing state, while `--clear-artist-cache` flushes the artist romanisation cache; operations continue even if cache eviction encounters recoverable errors.
- **Collect unprocessed files**: After organising `music_path`, any files still located under the source tree move to `<music_path>/<unprocessed_dir_name>/...`, preserving their original relative paths so users can review leftovers; the default folder name is `!unprocessed` and can be overridden in the config file. Files that are already in their target location are counted as processed and remain in place, and the CLI reports `Unprocessed files awaiting review: <count>` at the end of each organise run.

## Flows
- **Primary organise flow**: CLI parsing → configuration load → construct `OrganizeMusicService` → build a `MusicProcessor` that wires together metadata extraction, artist romanisation, duplicate detection, directory generation, and file-name generation (`DirectoryGenerator`, `FileNameGenerator`) → enumerate supported files and schedule romanisation lookups → extract metadata (Mutagen) with optional MusicBrainz romanisation → compute target paths → move audio/lyrics/artwork via filesystem adapters → persist `processing_before/after` rows → emit Rich console summary.
- **Restore flow**: CLI parsing → build `RestoreMusicService` request → load persisted plan from SQLite (`processing_after` + path elements) → evaluate collision policy (abort/skip/backup) → move or copy files back to origin/destination → optionally purge state.
- **Error and retry handling**: Metadata extraction or IO failures mark the result unsuccessful, skip the file, and continue processing. Rate-limited MusicBrainz lookups obey 1 req/s with a single retry on 429/5xx and downgrade to local naming when network calls fail. Keyboard interrupts exit with code 130 after logging.
- **Dry-run flow**: All filesystem operations short-circuit to planning only, but metadata extraction, hashing, and logging still execute for parity with real runs.

## Non-functional Requirements
- Capable of processing tens of thousands of files on a modern laptop using bounded worker pools and streaming IO without exceeding available memory.
- Operates entirely offline after dependencies are installed; romanisation degrades gracefully when outbound HTTP is blocked.
- File moves are atomic per filesystem (rename when same device, copy + fsync + remove otherwise) to maintain integrity.
- Logging follows module-specific loggers with structured event identifiers to aid downstream analysis; CLI output uses Rich with ANSI-aware formatting.
- Supports Windows, macOS, and Linux path semantics by sanitising filenames and normalising Unicode.

## Artist Override Configuration
- Override resolution honours the precedence `user preferences → persistent cache → MusicBrainz → pykakasi transliteration`.
- Users can provide preferred artist names at `config/artist_name_preferences.toml`; set `OMYM_ARTIST_NAME_PREFERENCES_PATH` to point elsewhere.
- The loader accepts a minimal TOML document:
  ```toml
  metadata_version = 1

  [defaults]
  locale = "en_US"

  [preferences]
  "宇多田ヒカル" = "Utada Hikaru"
  Perfume = "Perfume"
  ```
- Keep the document to simple key/value pairs. Duplicate keys after case normalisation are rejected to avoid ambiguity, and blanks are retained as placeholders for later editing.
- A starter file is created automatically on first run at `config/artist_name_preferences.toml`. As you run dry-run or organise commands, encountered artists are appended with empty values for quick editing.
- Run targeted tests with `uv run pytest tests/config/test_artist_name_preferences.py` after editing preference logic.

## Assumptions, Constraints, Dependencies
- Requires Python ≥3.13 with dependencies pinned in [`pyproject.toml`](../pyproject.toml) and managed via `uv`.
- Expects all files on locally mounted filesystems accessible by the running user; network shares are treated as opaque POSIX/NTFS mounts.
- SQLite database lives under `OMYM_DATA_DIR` (default `.data/`) and is accessed in-process without concurrent writers.
- Optional HTTP integration with MusicBrainz honours the project's user-agent policy and rate limits.

## Test Ideas / Examples
- `uv run pytest` covering metadata extraction, path generation, duplicate detection, restoration planning, and cache clearing logic.
- Golden-directory fixtures combining audio, `.lrc`, and artwork ensure linked assets follow their tracks across organise and restore cycles.
- Simulation of hash collisions and existing destination files verifies each collision policy behaves as expected.
- Fault injection (missing tags, unreadable files, network errors) to confirm graceful degradation and accurate CLI exit codes.
