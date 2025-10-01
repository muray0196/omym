# omym

Audio library ingestion, organisation, and restoration toolkit.

## Getting Started
1. Sync dependencies (UV recommended):
   ```bash
   uv sync --group dev
   ```
2. Run static analysis:
   ```bash
   uv run basedpyright
   ```
3. Execute tests (layer markers optional):
   ```bash
   uv run pytest
   uv run pytest -m "domain or usecase"
   uv run pytest -m integration
   ```

## Architecture at a Glance
- **Feature-oriented hexagonal layout**: `src/omym/features/<feature>/{domain,usecases,adapters}` owns business rules, application services, and infrastructure adapters per capability (current features: `metadata`, `organization`, `path`, `restoration`).
- **Cross-cutting services**: `src/omym/platform` hosts shared technical helpers (database manager, filesystem, logging, HTTP clients). `src/omym/shared` contains reusable domain primitives and error types.
- **UI adapters**: `src/omym/ui` (CLI today, room for HTTP/GUI) invoke feature use cases only.
- **Configuration**: `src/omym/config` materialises typed settings from `config/config.toml` and environment variables.

### Layering Rules
- Feature `domain` modules depend on `shared` only.
- Feature `usecases` import their own domain modules, `shared`, and port protocols.
- Feature `adapters` call into `platform` helpers and implement ports; they never depend on other features.
- `platform` and `shared` remain free of feature imports (enforced by static analysis).

## Documentation
- Architectural decisions live in [`docs/architecture.md`](docs/architecture.md).
- Directory responsibilities are listed in [`docs/repo-map.md`](docs/repo-map.md).
- Feature ADRs belong under `docs/adr/` (create as needed).

## Inspect Artist Preferences
- `uv run python -m omym preferences --only-missing` lists artists that still need a preferred romanised name or cached lookup.
- Add `--all` to review every configured or cached artist alongside the recorded source.
- Example output:
  ```text
  +--------------+-----------+----------+------------+--------------------+
  | Artist       | Preferred | Cached   | Source     | Status             |
  +--------------+-----------+----------+------------+--------------------+
  | 宇多田ヒカル  | Utada ... | Utada ...| musicbrainz| synced             |
  | 東京事変      | N/A       | Tokyo ...| manual     | needs preference   |
  +--------------+-----------+----------+------------+--------------------+
  ```

## Contributing
- Update docs alongside code changes.
- Keep commits focused on a single feature migration step.
- Use feature branches and ensure `uv run basedpyright` and `uv run pytest` pass before pushing.
