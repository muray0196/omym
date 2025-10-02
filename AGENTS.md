<role>
You are an AI assistant specialized in Python development.
</role>

<architecture>
- Pattern: Feature-oriented Hexagonal Architecture.
- Directory layout:
  - features/$feature/{domain,usecases,adapters}
  - Cross-cutting concerns in platform/ and shared/
- Dependency direction: adapters → usecases → domain
- Purity rule: No I/O in domain or usecases.
</architecture>

<configuration_policies>
- Config source: environment variables only.
- Validation: validate config at process startup; fail fast on invalid/missing values.
- Paths: all config/data paths are relative to the repository root to ensure portability.
- Legacy: NEVER retain backward-compatibility layers or legacy paths; remove immediately when encountered.
</configuration_policies>

<code_quality>
- Logging : use Python’s standard logging module
- Typing : run `uv run basedpyright` after implementation
- Suppressions (SHOULD NOT): use `# pyright: ignore[...]` sparingly; each suppression MUST include a brief justification comment.
- Tests: use `pytest` and `pytest-mock` only
- Complex tests: include a brief intent docstring describing the behavior under test and key edge cases.
</code_quality>

<testing_flow>
- Quick global check (MUST): `uv run pytest -q --maxfail=1 --tb=line --show-capture=stdout`
- Inspect failure (SHOULD): `uv run pytest TEST_TARGET -q --tb=short --show-capture=all`
- Deep debug (MAY): `uv run pytest TEST_TARGET -q --tb=long -s --show-capture=all`
</testing_flow>

<decision_logic>
IF code change touches time-, file-, or network-boundaries → put logic in adapters.
ELSE IF a dependency would invert adapters→usecases→domain → refactor or introduce a port/interface.
ELSE proceed within the current layer.
</decision_logic>

<examples>
<example label="good">
* Added S3 client in adapters, introduced UseCase interface for file retrieval, pure domain validator.
* Config validated at startup; missing AWS_REGION fails fast.
* Tests with pytest-mock to stub S3; intent docstring clarifies retry semantics.
</example>

<example label="bad">
* Domain object reads environment variables directly.
* Added `print()` debugging and skipped type checking warnings with blanket ignores.
* Tests use unittest + random time.sleep() calls.
</example>