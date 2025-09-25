# Module Slimming Plan

**Where:** docs/module-slimming-plan.md  
**What:** Action plan to reduce oversized Python modules exceeding 300 LOC.  
**Why:** Align the codebase with maintainability guidelines that mandate small, focused files.

## Overview
- Target files currently over 300 LOC: `music_file_processor.py`, `music_file_renamer.py`, `logger.py`, and `test_music_file_processor.py`.
- Goal: Refactor into cohesive modules below 300 LOC while keeping behavior stable and dependencies directional.
- Constraints: No new dependencies, centralize tunables in `config.py`, ensure hexagonal boundaries remain intact.

## Step-by-Step Plan

1. **Map Responsibilities**
   - Read each target module end-to-end.
   - Record responsibility blocks, collaborators, and implicit contracts.
   - Sketch dependency edges to spot potential cycles before splitting.

2. **Design Splits**
   - Propose submodules (~250 LOC each) grouped by responsibility:
     - `music_file_processor` package:
       - `events.py`: `ProcessingEvent`, event-to-style mappings, logging extras builders.
       - `context.py`: `ProcessingLogContext`, shared progress accounting helpers.
       - `results.py`: dataclasses for process outcomes (music, lyrics, artwork) plus warning summarizers.
       - `artist_cache.py`: `_DryRunArtistCacheAdapter` and cache-related helpers.
       - `romanization.py`: scheduling/await helpers that orchestrate `ArtistRomanizer` futures.
       - `processor.py`: lean `MusicProcessor` coordinating collaborators via injected helpers.
     - `music_file_renamer` package:
       - `artist_id.py`: `ArtistIdGenerator` with transliteration utilities.
       - `cached_artist_id.py`: cache-aware wrapper and validation utilities.
       - `filename.py`: file-name generation with album caches.
       - `directory.py`: directory generation, album-year tracking.
     - `platform.logging` package:
       - `handlers.py`: `WhitePathRichHandler` and Rich rendering utilities.
       - `config.py`: `setup_logger`, default file configuration, environment hooks.
     - Tests reorganized under `tests/features/metadata/music_processor/`:
       - `test_process_file_success.py`, `test_process_file_failures.py`, `test_directory_processing.py`, `test_romanization.py`, `test_injected_ports.py`, `test_dry_run.py`.
   - Define public API (exports) for each new module; document transitions.

3. **Verify External APIs**
   - Use `context7` docs to confirm current interfaces for `pykakasi`, `langid`, `rich`, and stdlib modules relied upon.
   - Identify any API changes that influence module boundaries.

## Responsibility Notes (2025-09-25 review)
- `music_file_processor.py`: mixes orchestration, caching adapters, dataclasses, logging events, filesystem helpers, romanization scheduling; high cyclomatic hotspots inside `_process_associated_*` and directory commit/rollback handling.
- `music_file_renamer.py`: combines transliteration, Artist ID rules, cache storage, filename/disc logic, and directory/year aggregation; shared caches stored as class vars that must migrate carefully.
- `platform/logging/logger.py`: couples Rich handler rendering with global logger bootstrap and config defaults; emoji styling tables co-located with handler.
- `tests/features/metadata/test_music_file_processor.py`: monolithic integration tests plus unit coverage for private helpers; uses fixtures heavily and mutates mocks inline, making intent hard to scan.

## External API Checkpoints
- `rich` (Textualize): Retrieved logging handler docs via context7 to validate continued availability of `RichHandler`, `rich_tracebacks`, and custom renderable support; safe to refactor handler subclass into dedicated module.
- `pykakasi`, `langid`: No context7 entries located (2025-09-25). Proceed assuming current APIs match existing usage, but document risk and consider pinning versions or adding smoke tests around transliteration/language detection helpers during refactor.

4. **Implement Iteratively**
   - Refactor the least coupled file first (`logger`), extracting handlers and ensuring `config.py` supplies tunables.
   - Proceed to `music_file_renamer`, splitting generators and sanitization helpers.
   - Tackle `music_file_processor` last, isolating data models and side-effect orchestration to minimize churn.
   - Add file headers summarizing Where/What/Why and inline comments for non-obvious flows.

5. **Restructure Tests**
   - Break `test_music_file_processor.py` into scenario-specific modules with intent docstrings.
   - Update fixtures/imports to match new module layout.
   - Add or adjust tests to cover newly separated components.

6. **Continuous Verification**
   - After each refactor slice, run `uv run pytest <target>` and `uv run basedpyright`.
   - Ensure configuration constants live in `config.py`; replace magic numbers accordingly.

7. **Documentation & Reflection**
   - Update relevant docs (e.g., `docs/architecture.md` or new notes) to describe the new structure.
   - Capture residual risks, assumptions, and next steps for future work.

## Execution Log
- 2025-09-25: Split `platform/logging` into `handlers.py` and `config.py`, wiring canonical exports via `omym.platform.logging`; verified with `uv run pytest tests/platform/logger` and `uv run basedpyright`.
- 2025-09-25: Extracted renamer utilities into `features/path/usecases/renamer/` package and updated imports to the new package; verified with `uv run pytest tests/features/path tests/platform/db/cache/test_artist_cache_dao.py` and `uv run basedpyright`.
- 2025-09-25: Removed all backward-compatibility facades and confirmed canonical import paths; reran targeted pytest suite and basedpyright.

## Deliverables
- Refactored modules each under 300 LOC with preserved behavior.
- Updated tests aligned with the new structure.
- Documentation outlining the new module boundaries and any remaining follow-ups.

## Risks & Mitigations
- **Risk:** Hidden coupling could cause regressions. **Mitigation:** Incremental refactors with tests at each stage.
- **Risk:** Breaking external integrations. **Mitigation:** Verify public APIs and maintain adapter interfaces.
- **Risk:** Test gaps after splitting. **Mitigation:** Add docstrings clarifying intent and cover edge cases during split.
