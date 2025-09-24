owner: Maintainers
status: active
last_updated: 2025-09-24
review_cadence: quarterly

## Architectural Overview
- **Entry points**: `python -m omym` and the packaged console script delegate to `omym.ui.cli.main`. GUI experiments remain thin adapters that re-use the CLI feature orchestration.
- **Feature-oriented hexagonal layout**: Business logic is grouped by capability under `src/omym/features/<feature>`. Each feature owns:
  - `domain/`: entities, value objects, and pure domain services scoped to the feature (no outbound dependencies except `shared/`).
  - `usecases/`: application services, commands/queries, and port definitions that orchestrate domain behaviour.
  - `adapters/`: infrastructure-facing implementations (DB, filesystem, MusicBrainz, logging) bound to ports.
- **Cross-cutting layers**:
  - `platform/`: shared technical services (SQLite manager, filesystem primitives, logging bootstrap, configuration providers). Modules here may depend on the standard library and third-party integrations but never on feature packages.
  - `shared/`: reusable domain primitives (value objects, error types, functional helpers) that remain framework-free and immutable where possible.
  - `config/`: boot-time configuration surface that instantiates typed settings via environment variables and TOML defaults. Feature packages receive settings through dependency injection.

## Feature Catalog and Flows
- **Ingestion**: prepares raw audio inputs, validates checksum manifests, and registers files for downstream organisation.
- **Organization**: arranges tracks into album/disc hierarchies, maintains ordering metadata, and delegates to the path feature for filesystem-safe locations.
- **Path**: generates canonical directory/filename structures, handles artist ID generation, and sanitises user-provided metadata for filesystem compatibility.
- **Restoration**: plans and executes file restores with collision policies and rollback support.
- **Metadata enrichment**: augments tags, resolves duplicates, and integrates with MusicBrainz for romanisation and artist profiles.
- Features communicate solely through ports exposed at their `usecases` boundary; direct cross-feature imports are forbidden.

### Dependency Rules
- `features/*/domain` → `shared` only.
- `features/*/usecases` → same feature `domain`, `shared`, and port protocols.
- `features/*/adapters` → `platform`, same feature `usecases`, and standard library / third-party clients.
- `platform` and `shared` never depend on feature packages or each other (only standard library / approved libraries).
- UI adapters (`ui/cli`, future HTTP/gRPC) call `features/<feature>/usecases` services exclusively.

### Execution Flow Example
1. CLI parses arguments and resolves a feature-specific use case (e.g., `features/restoration/usecases/execute_restore.py`).
2. The use case instantiates domain services and requests backing ports (repositories, filesystem gateways) from dependency injection helpers.
3. Ports are fulfilled by adapters that wrap `platform` helpers (SQLite, MusicBrainz client, file IO).
4. Results propagate back to the UI layer with structured status events for logging and telemetry.

## Data Model and Schemas
- SQLite schema resides in [`src/omym/platform/db/migrations/schema.sql`](../src/omym/platform/db/migrations/schema.sql) and is applied via the shared `DatabaseManager` during platform bootstrapping.
- Key tables:
  - `processing_before` and `processing_after` capture file hashes, source paths, derived metadata, and restore targets for auditability.
  - `albums` and `track_positions` persist album/disc relationships and track ordering semantics.
  - `filter_hierarchies` and `filter_values` track user-defined organisation filters.
  - `artist_cache` stores romanised artist names and aliases sourced from MusicBrainz.
- Indices optimise hash and hierarchy lookups. The database file defaults to `.data/omym.db`, overridable via `OMYM_DATA_DIR`.

## External Integrations
- **Mutagen**: audio metadata extraction across MP3, FLAC, AAC/M4A, DSF, ALAC, and Opus.
- **MusicBrainz WS2 API**: optional artist romanisation with rate limiting and caching adapters.
- **Rich**: CLI presentation (tables, colours, progress feedback).
- Standard library `shutil`, `hashlib`, `pathlib`, and `concurrent.futures` underpin file IO, hashing, and parallel work units.

## Configuration and Secrets
- Boot configuration loads typed settings from `config/config.toml`, overridden by environment variables such as `OMYM_DATA_DIR` and `MUSICBRAINZ_USER_AGENT`.
- Settings are materialised in `platform/config` and passed explicitly to feature use cases or adapters.
- No secrets are stored; operators must configure MusicBrainz credentials externally when needed.

## Observability
- Logging is initialised in `platform/logging` to emit structured events consumed by feature adapters.
- Use cases surface progress and error details via typed result objects enabling CLI and future UI adapters to provide consistent reporting.
- MusicBrainz integration captures rate-limit and parsing warnings without failing the pipeline.

## Runtime, Build, and Deploy
- Runtime: Python ≥3.13 on POSIX or Windows. File moves handle cross-device scenarios by fallback copy + fsync + remove semantics.
- Dependency management: `uv` (see [`pyproject.toml`](../pyproject.toml)).
- Quality gates: `uv run basedpyright` and `uv run pytest`. CI mirrors these checks; layers use pytest markers to isolate feature, integration, and smoke suites.
- Packaging: standard `src/` layout. Console entry points invoke feature use cases through adapters only.

## Compatibility / Support Policy
- Supported platforms: modern Windows, macOS, Linux with UTF-8 filesystems.
- Backward compatibility: schema migrations apply automatically; deprecated flows are removed rather than wrapped. Restore capability depends on persisted hashes—deleting the SQLite database invalidates historical recovery plans.
- Designed for single-user, single-process execution. Concurrent runs require separate data directories to avoid SQLite locking.
