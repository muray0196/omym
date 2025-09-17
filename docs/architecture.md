owner: Maintainers
status: draft
last_updated: 2025-09-03
review_cadence: quarterly

## System and Module Boundaries
- Entry point `omym.main:main` provides a CLI interface.
- `core` handles metadata extraction, path generation, and file organization, and now includes restoration orchestration built atop the same data layer.
- `db` contains SQLite access layers and migrations.
- `ui` renders console output using Rich.
- `utils` supplies helpers such as filename sanitization.

## Data Model and Schemas
- SQLite database stores path elements and processing state.
- Migrations live in `omym/db/migrations` and are applied through `db_manager.py`.

## External Integrations
- Uses Mutagen for audio metadata.
- Language detection and transliteration rely on LangID, PyKakasi, and Unidecode.

## Configuration and Secrets
- `config.py` reads environment variables for runtime settings; no secrets are persisted.

## Observability
- Standard logging is configured per PEP 282 with module-level loggers.

## Runtime, Build, and Deploy
- Targets Python ≥3.13.
- Development tasks use `uv run basedpyright` and `uv run pytest`.
- Packaged via Setuptools; CI is expected through GitHub Actions.

## Compatibility / Support Policy
- Intended for local execution on Linux, macOS, and Windows file systems.
