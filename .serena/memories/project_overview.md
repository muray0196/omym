# Project: OMYM (Organize My Music)

## Purpose
A Python CLI that organizes a local music library by extracting and normalizing metadata, generating a consistent directory/filename layout, and tracking state in a portable SQLite database under the repository (or a custom data dir).

## Tech Stack
- Language: Python 3.13
- CLI: `argparse` with an entrypoint `omym` (mapped to `omym.main:main`)
- TUI/Logs: `rich`
- Metadata: `mutagen` (+ helpers: `unidecode`, `pykakasi`, `langid`)
- DB: SQLite via `sqlite3`, initialized on first connection
- Build/Run: `uv`
- Static typing: `basedpyright`
- Tests: `pytest` (+ `pytest-cov`)

## High-level Architecture
- `src/omym/ui/cli`: CLI argument parsing, command dispatch, display helpers
- `src/omym/domain`: Core domain logic (path generation, sanitizing, metadata, organization)
- `src/omym/infra`: Infrastructure (logging, DB access, migrations, caches)
- `src/omym/config`: Portable paths + config loader/saver
- `tests/`: Mirrors the above and covers CLI, domain, infra, and config behavior
- `docs/`: Product/architecture docs

## Entrypoints
- Package entrypoint: `omym` (from `[project.scripts]` in `pyproject.toml`)
- Module entrypoint: `python -m omym`
- Main callable: `omym.ui.cli.cli:main()`

## Data & Config Layout (portable by default)
- Config: `<repo_root>/.config/omym/config.toml`
- Data (SQLite DB): `<repo_root>/.data/omym.db`
- Override data dir: env `OMYM_DATA_DIR=/path/to/data`

## Notable Paths/Files
- `pyproject.toml`: Python version, deps, scripts, type checker config
- `src/omym/infra/db/db_manager.py`: DB location rules + schema init
- `src/omym/ui/cli/args/parser.py`: CLI options and validation
- `README.md` and `docs/`: Product-level information

## Supported Formats (from README)
MP3, FLAC, M4A/AAC, DSF, Opus.
