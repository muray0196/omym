# OMYM (Organize My Music)

A Python tool to organize your music library by automatically processing metadata and organizing files into a consistent structure.

## Features

- Supports MP3, FLAC, M4A/AAC, DSF, Opus (.opus) formats
- Extracts and processes music metadata
- Synchronizes co-located .lrc lyric files with their tracks
- Creates organized folder structure
- Handles multi-disc albums and compilations
- Sanitizes filenames for cross-platform compatibility
- Restores previously organized files to their original locations or a new target

## Usage

```bash
# Organize files or directories
uv run python -m omym organize /path/to/music --target /dest/library

# Preview the restore plan without moving files
uv run python -m omym restore /dest/library --dry-run

# Restore files back to their original paths recorded in the database
uv run python -m omym restore /dest/library --purge-state
```

Use `--collision-policy` (`abort`, `skip`, or `backup`) to control how existing files at the destination are handled during restore. The default behaviour is `abort`.

## Continuous Integration

Automated quality checks run in GitHub Actions via `.github/workflows/ci.yml`. The pipeline uses `uv` to create the project environment on Python 3.13, executes `uv run basedpyright` for static analysis, and finishes with `uv run pytest --cov=src --cov-report=xml`. To reproduce the same checks locally:

```bash
uv sync --group dev
uv run basedpyright
uv run pytest --cov=src --cov-report=xml
```
