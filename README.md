# OMYM (Organize My Music)

A Python tool to organize your music library by automatically processing metadata and organizing files into a consistent structure.

## Features

- Supports MP3, FLAC, M4A/AAC, DSF, Opus (.opus) formats
- Extracts and processes music metadata
- Creates organized folder structure
- Handles multi-disc albums and compilations
- Sanitizes filenames for cross-platform compatibility

## Continuous Integration

Automated quality checks run in GitHub Actions via `.github/workflows/ci.yml`. The pipeline uses `uv` to create the project environment on Python 3.13, executes `uv run basedpyright` for static analysis, and finishes with `uv run pytest --cov=src --cov-report=xml`. To reproduce the same checks locally:

```bash
uv sync --group dev
uv run basedpyright
uv run pytest --cov=src --cov-report=xml
```
