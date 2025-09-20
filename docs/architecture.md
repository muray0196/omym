owner: Maintainers
status: active
last_updated: 2025-09-17
review_cadence: quarterly

## System and Module Boundaries
- **Entry points**: `python -m omym` invokes `omym.ui.cli.main`, which delegates to the CLI command processor. A thin GUI facade exists under `ui/gui` but currently re-exports the CLI services.
- **UI layer (`omym.ui`)**: `ui.cli` owns argument parsing, Rich-powered console feedback, and progress reporting. It calls into application services and never touches infra types directly.
- **Application layer (`omym.application.services`)**: Facades that construct domain services (`OrganizeMusicService`, `RestoreMusicService`), apply cache maintenance semantics, and translate CLI arguments into domain requests.
- **Domain layer (`omym.domain`)**: Encapsulates core behaviour.
  - `metadata` handles tag extraction (Mutagen), romanisation, hashing, duplicate detection, and orchestration through `MusicProcessor` with a bounded `ThreadPoolExecutor` for IO tasks.
  - `path` computes sanitised directory/file layouts and manages artist/album identifiers.
  - `organization` groups tracks into albums, discs, and filter hierarchies backed by SQLite metadata.
  - `restoration` builds and executes restore plans with collision-policy aware file operations.
  - `common` contains cross-cutting helpers such as directory cleanup.
- **Infrastructure layer (`omym.infra`)**:
  - `db` exposes the SQLite connection manager, DAO classes for processing metadata, album grouping, maintenance, and artist romanisation cache.
  - `musicbrainz` implements the WS2 HTTP client with rate limiting and optional `requests` usage, plus pluggable cache registration.
  - `logger` configures module-level loggers.
- **Configuration (`omym.config`)** centralises config file discovery (`config/config.toml`), environment overrides (`OMYM_DATA_DIR`, `MUSICBRAINZ_USER_AGENT`), and runtime switches (`USE_MB_ROMANIZATION`).

## Data Model and Schemas
- SQLite schema lives in [`src/omym/infra/db/migrations/schema.sql`](../src/omym/infra/db/migrations/schema.sql) and is applied via `DatabaseManager` during processor initialisation.
- Key tables:
  - `processing_before` and `processing_after` record file hashes, source paths, derived metadata, and targets for auditing and restore planning.
  - `albums` and `track_positions` persist album/disc relationships and track ordering.
  - `filter_hierarchies` and `filter_values` support configurable directory filters.
  - `artist_cache` stores romanised artist names and aliases sourced from MusicBrainz.
- Indices optimise lookups by hash and hierarchy. The database file resides under `.data/omym.db` by default.

## External Integrations
- **Mutagen** for reading audio metadata across MP3, FLAC, AAC/M4A, DSF, ALAC, and Opus formats.
- **MusicBrainz WS2 API** for optional artist romanisation (guarded by rate limiting and fallback logic).
- **Rich** for CLI presentation (tables, colours, progress).
- Standard library `shutil`, `hashlib`, and `pathlib` underpin file operations and hashing; no other network services are contacted.

## Configuration and Secrets
- Configuration is stored in TOML at `config/config.toml`; the file is created with comments on first run if absent.
- `OMYM_DATA_DIR` overrides the default `.data/` directory for the SQLite database and cache files.
- `MUSICBRAINZ_USER_AGENT` allows operators to supply a custom UA; otherwise values fall back to the TOML-configured app identity.
- No secrets are persisted. Users must ensure the configured contact information complies with MusicBrainz etiquette.

## Observability
- Logging is emitted through `omym.infra.logger.logger` with structured event identifiers defined in `ProcessingEvent`. Messages are console-friendly yet machine-parseable.
- CLI summaries highlight processed/skipped/failed counts and propagate error reasons for actionable follow-up.
- MusicBrainz warnings capture rate-limiting and JSON parsing failures without aborting processing.

## Runtime, Build, and Deploy
- Runtime: Python ≥3.13 on POSIX or Windows. File moves respect cross-device constraints by performing copy + fsync + remove when necessary.
- Dependency management: `uv` (see [`pyproject.toml`](../pyproject.toml)) with optional extras resolved at sync time.
- Quality gates: `uv run basedpyright` for static typing and `uv run pytest` for tests. CI mirrors these checks in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
- Packaging: standard Python package (`src/` layout) consumable via `pip install .` after `uv build`.

## Compatibility / Support Policy
- Supported platforms: modern Windows, macOS, and Linux distributions with UTF-8 filesystems.
- Backward compatibility: schema migrations run automatically; obsolete paths are removed rather than maintained. Restore operations rely on recorded hashes, so deleting the SQLite database invalidates recovery ability.
- Designed for single-user, single-process execution. For concurrent runners, users must provision separate data directories to avoid locking conflicts.
