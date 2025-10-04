owner: Maintainers
status: active
last_updated: 2025-09-26
review_cadence: quarterly

## Architectural Overview
- **Entry points**: `python -m omym` and the console script invoke `omym.ui.cli.main`, which resolves an application service in `src/omym/application/services`. UI surfaces never construct feature adapters directly.
- **Feature-oriented hexagonal layout**: Business logic is grouped under `src/omym/features/<feature>`, and every feature contains:
  - `domain/`: entities, value objects, and pure domain services scoped to the capability (only depends on `shared/`).
  - `usecases/`: application services plus port protocols that orchestrate the feature's domain logic.
  - `adapters/`: infrastructure-facing implementations (SQLite repositories, filesystem gateways, external API clients) bound to the declared ports.
- **Cross-cutting layers**:
  - `platform/`: shared technical services (database manager, filesystem primitives, logging bootstrap, MusicBrainz HTTP client). Modules here depend on standard libraries or vetted third-party packages and never import feature code.
  - `shared/`: feature-agnostic domain primitives, typed results, and error hierarchies that remain framework-free and immutable where possible.
  - `config/`: typed configuration loaders that hydrate settings from environment variables and repository-relative TOML defaults; features receive settings via dependency injection helpers.

## Feature Catalog and Flows
- **Metadata** (`src/omym/features/metadata`): extracts and enriches tags via `MusicProcessor`, coordinates optional MusicBrainz lookups, emits processing events consumed by organisation flows, and surfaces database/cache ports in `usecases/ports.py` so adapters remain swappable. The use case now composes dedicated helper packages (`usecases/assets/` for lyrics and artwork flows, `usecases/processing/` for orchestration, cleanup, and shared result types) to keep each module under 300 LOC while preserving the existing public API. Dry-run artist cache wiring lives in `adapters/artist_cache_adapter.py` so use cases stay free of platform database imports.
- **Organization** (`src/omym/features/organization`): groups tracks into album/disc hierarchies, evaluates user-defined filters, composes metadata and path services to derive final layouts, and exposes album/filter repository ports in `usecases/ports.py` with SQLite adapters now living under `adapters/`.
- **Path** (`src/omym/features/path`): generates filesystem-safe directory and filename structures, sanitises inputs, exposes helpers that organisation and restoration use to resolve canonical targets, and now publishes filter access ports in `usecases/ports.py`.
- **Restoration** (`src/omym/features/restoration`): reconstructs original locations from persisted processing plans, applies collision policies, and coordinates filesystem/database adapters for rollback.
- Features collaborate exclusively through ports defined in their `usecases` modules. For example, the organisation use cases consume `MetadataExtractor` and path generation ports rather than importing foreign domains directly.

### Dependency Rules
- `features/*/domain` → `shared` only.
- `features/*/usecases` → same-feature `domain`, `shared`, and declared port protocols.
- `features/*/adapters` → `platform`, same-feature `usecases`, and approved third-party clients.
- `platform` and `shared` never depend on feature packages or on each other.
- UI adapters (`ui/cli`, future HTTP/gRPC) call into application services which, in turn, delegate to feature use cases.

### Execution Flow Example
1. CLI parses arguments and resolves an application service (for example, `OrganizeMusicService`).
2. The application service instantiates the required feature use case (`MusicProcessor`, `MusicGrouper`, etc.) with injected ports.
3. Ports are fulfilled by adapters that wrap `platform` helpers (SQLite repositories, filesystem abstractions, MusicBrainz client).
4. Results propagate back to the UI layer via structured status events for logging and telemetry.

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
- Boot configuration loads typed settings from `src/omym/config/settings.py`, which hydrates defaults from `config/config.toml` and overrides via environment variables (e.g., `OMYM_DATA_DIR`, `MUSICBRAINZ_USER_AGENT`).
- File hashing throughput is tuned via the `file_hash_chunk_size` config entry (default 131,072 bytes) to balance memory usage and IO throughput.
- Settings objects are passed into application services and adapters explicitly; features never read environment variables directly.
- No secrets are stored; operators configure MusicBrainz credentials externally when needed.

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
