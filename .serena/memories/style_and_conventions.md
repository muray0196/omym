# Style & Conventions

## Coding Standards
- PEP 8 for style; readable, maintainable code (no clever one-liners for critical logic)
- PEP 484 type hints everywhere (functions, methods, variables). Prefer explicit types over `Any`
- Data classes (PEP 557) where appropriate (e.g., CLI `Args`)
- Docstrings follow Google style with clear Args/Returns/Raises sections
- Logging per PEP 282; centralized logger via `omym.infra.logger` with Rich console output
- Avoid `# pyright: ignore` unless absolutely necessary and include a justification comment

## Project Layout
- Separate modules for `domain`, `infra`, `ui`, and `config`
- Tests mirror code structure under `tests/`
- All code and docs in-repo are English

## Error Handling
- Fail fast on invalid CLI inputs (nonexistent path, missing target) with clear error messages and non-zero exit
- Wrap unexpected exceptions at CLI boundary; exit with status 1; use informative logs

## Config & Paths Policy
- Config file path is fixed (no CLI override): `<repo>/.config/omym/config.toml`
- Data dir defaults to `<repo>/.data`; can be overridden by `OMYM_DATA_DIR`

## DB
- SQLite schema initialized automatically on connect; WAL mode; FK enforced; busy timeouts configured

## Commit/Review Checklist (excerpt)
- Add/update docstrings for public functions
- Maintain typing (no regressions in basedpyright)
- Keep domain logic pure and deterministic where feasible; side effects live in infra
