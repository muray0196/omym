owner: Maintainers
status: active
last_updated: 2025-09-24
review_cadence: quarterly

## Top-level Structure
- [`src/`](../src): Python source root.
  - [`omym/features/`](../src/omym/features): Feature-oriented packages combining domain, use case, and adapter slices. Current features: `metadata`, `organization`, `path`, `restoration`.
    - `domain/`: pure business rules for the feature.
    - `usecases/`: application services, commands, queries, and port protocols.
        - `processing/`: directory and file orchestration plus shared flow types.
        - `assets/`: lyrics and artwork asset discovery, logging, and summarisation.
        - `file_management/`: file hashing, duplicate handling, and target path utilities.
        - `cleanup/`: post-run lifecycle helpers for unprocessed material.
    - `adapters/`: infrastructure implementations (DB, filesystem, external APIs) that fulfil ports.
  - [`omym/platform/`](../src/omym/platform): Cross-cutting technical services—database manager, filesystem primitives, logging bootstrap, configuration providers, MusicBrainz HTTP client.
    - `musicbrainz/`: split into focused modules (`http_client`, `rate_limit`, `romanization`, `cache`, `user_agent`) with `client.py` acting as the public façade.
  - [`omym/shared/`](../src/omym/shared): Feature-agnostic value objects, typed results, error types, functional helpers.
  - [`omym/ui/`](../src/omym/ui): CLI and experimental GUI adapters that call feature use cases only.
  - [`omym/config/`](../src/omym/config): Typed configuration loading (environment + TOML defaults) fed into `platform` and feature factories.
- [`tests/`](../tests): Pytest suite organised by layer.
  - `tests/features/<feature>/` for domain and use case tests (ports mocked).
  - `tests/platform/` for shared infrastructure tests.
  - `tests/integration/` for adapter + platform wiring.
- [`docs/`](./): Living design docs ([spec](spec.md), [architecture](architecture.md), [glossary](glossary.md))
- [`.github/workflows/`](../.github/workflows): CI pipeline definition.
- [`pyproject.toml`](../pyproject.toml): Tooling configuration and dependency metadata.
- [`README.md`](../README.md): High-level usage guide and quick-start instructions.
- **Generated at runtime (not versioned)**: `config/config.toml` for user settings and `.data/omym.db` for the SQLite database; both default to repository-relative paths and may be overridden via env vars.

## Naming Conventions
- Packages and modules use lowercase with underscores; classes use PascalCase.
- Tests follow `test_*.py` and mirror package names.
- CLI options use kebab-case (e.g., `--clear-cache`), and preview runs are exposed via the `plan` subcommand.

## Common Commands
- Install & sync dependencies: `uv sync --group dev`.
- Static analysis: `uv run basedpyright`.
- Run unit tests: `uv run pytest`.
- Format docs or code: follow PEP 8 and use editor tooling (no repo-wide formatter configured).

## Code Ownership & Practices
- Maintainers own all packages; contributors must update docs alongside code changes.
- Changes affecting command behaviour or schema must update [`docs/spec.md`](spec.md) and [`docs/architecture.md`](architecture.md).
- Use feature branches locally, but submit pull requests from a clean mainline-compatible history.
