> You are an AI assistant specialized in Python development.

## Architecture
- Feature-oriented hexagonal: `features/<feature>/{domain,usecases,adapters}`; cross-cutting in `platform/` and `shared/`.
- One-way deps: `adapters → usecases → domain`. No I/O in domain/usecases.

## Configuration & Policies
- Config via environment variables (validate at startup).
- All config/data paths live under repo root (portable).
- No backward-compatibility layers—remove legacy paths immediately.

## Code Quality
- Typing with `basedpyright`; avoid `Any`.
- Logging via stdlib.
- Use `# pyright: ignore[...]` sparingly, with justification.

## Testing
- `pytest` + `pytest-mock` only.
- Complex tests include a brief intent docstring.

## Commands
```bash
uv run basedpyright
uv run pytest <test_target>
```