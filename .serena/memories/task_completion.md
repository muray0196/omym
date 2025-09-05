# Task Completion Checklist

Use this before opening a PR or handing off work:

## Mandatory
- Type check passes: `uv run basedpyright`
- Tests pass locally: `uv run pytest -q` (add focused tests for new code)
- New/changed public APIs have Google-style docstrings
- Logging is informative but not noisy; no stray prints
- No dependency changes (per project policy); no environment assumptions beyond repo-root paths
- Config & data paths remain portable: use `default_config_path()` and `default_data_dir()`

## Recommended
- Add tests for primary code paths and edge cases
- Ensure CLI help string remains accurate: `uv run omym --help`
- If touching DB: schema consistency and migration scripts under `src/omym/infra/db/migrations/`
