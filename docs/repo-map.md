owner: Maintainers
status: draft
last_updated: 2025-09-03
review_cadence: quarterly

## Top-level Structure
- [`omym/`](../omym): library source code.
- [`tests/`](../tests): pytest test suite mirroring the source layout.
- [`docs/`](./): project documentation including [spec](spec.md) and [architecture](architecture.md).
- [`typings/`](../typings): type stubs for third-party libraries.
- [`pyproject.toml`](../pyproject.toml): project configuration and dependencies.
- [`README.md`](../README.md): high-level project overview.

## Naming Conventions
- Modules and packages use lowercase with underscores.
- Tests follow the pattern `test_*.py` under directories matching the source tree.

## Common Commands
- Type check: `uv run basedpyright`.
- Run tests: `uv run pytest`.

## Code Ownership
- Core modules and tests are owned by the maintainers; contributions should include updates to this document set.

