owner: Maintainers
status: active
last_updated: 2025-09-17
review_cadence: quarterly

## Top-level Structure
- [`src/`](../src): Application source using the `src` layout.
  - [`omym/ui/cli`](../src/omym/ui/cli): Argument parsing, command dispatch, and Rich-based output.
  - [`omym/application/services`](../src/omym/application/services): Organise/restore façades shared by all UIs.
  - [`omym/domain`](../src/omym/domain): Core business logic split into `metadata`, `path`, `organization`, `restoration`, and `common` helpers.
  - [`omym/infra`](../src/omym/infra): SQLite DAOs, MusicBrainz client, and logging utilities.
  - [`omym/config`](../src/omym/config): Config file loading, environment overrides, and runtime flags.
- [`tests/`](../tests): Pytest suite mirroring the source tree (UI, application, domain, config).
- [`docs/`](./): Living design docs ([spec](spec.md), [architecture](architecture.md), [glossary](glossary.md)); diagrams belong under [`docs/diagrams/`](diagrams/).
- [`.github/workflows/`](../.github/workflows): CI pipeline definition.
- [`pyproject.toml`](../pyproject.toml): Tooling configuration and dependency metadata.
- [`README.md`](../README.md): High-level usage guide.
- **Generated at runtime (not versioned)**: `config/config.toml` for user settings and `.data/omym.db` for the SQLite database; both live under the repository root by default and may be overridden via env vars.

## Naming Conventions
- Packages and modules use lowercase with underscores; classes use PascalCase.
- Tests follow `test_*.py` and mirror package names.
- CLI options use kebab-case (e.g., `--dry-run`, `--clear-cache`).

## Common Commands
- Install & sync dependencies: `uv sync --group dev`.
- Static analysis: `uv run basedpyright`.
- Run unit tests: `uv run pytest`.
- Format docs or code: follow PEP 8 and use editor tooling (no repo-wide formatter configured).

## Code Ownership & Practices
- Maintainers own all packages; contributors must update docs alongside code changes.
- Changes affecting command behaviour or schema must update [`docs/spec.md`](spec.md) and [`docs/architecture.md`](architecture.md).
- Use feature branches locally, but submit pull requests from a clean mainline-compatible history.
