# Suggested Commands (Linux, `uv`-based)

## Run the CLI
- Example (directory): `uv run omym "/path/to/MUSIC" --target "/path/to/ORGANIZED" --dry-run`
- Example (single file): `uv run omym "/path/to/file.flac" --target "/path/to/ORGANIZED"`
- Verbose logging: `--verbose` | quiet: `--quiet` | force ops: `--force`
- Maintenance: `--clear-artist-cache` | `--clear-cache` | DB preview flag: `--db`
- Alternative: `uv run python -m omym "/path/to/MUSIC" --target "/path/to/ORGANIZED"`

## Type Checking
- Run: `uv run basedpyright`

## Tests
- All tests: `uv run pytest -q`
- Filter by path: `uv run pytest tests/ui/cli -q`
- Filter by keyword: `uv run pytest -k "path_generator" -q`
- With coverage: `uv run pytest --cov=omym --cov-report=term-missing`

## Lint/Format (if available locally)
- Ruff (optional): `uv run ruff check .` and `uv run ruff format .`

## Data & Config
- Inspect DB: `sqlite3 .data/omym.db ".tables"`
- Override data dir (per shell): `export OMYM_DATA_DIR=/abs/path/to/data`

## Utilities
- List files (fast): `rg --files`
- Grep code: `rg "pattern" src/ tests/`
- View file sections: `sed -n '1,120p' src/omym/ui/cli/args/parser.py`
