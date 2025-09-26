# docs/ for AI coding assistants

Goal: Keep a minimal, high-signal doc set—prefer machine-readable contracts to prose while folding the previous six docs into three core files (optional UI guide allowed).

1. Spec & Flows (`docs/spec.md`)
   - Purpose: Combine PRD and tool-flow guidance so teams know what to build and expected behavior.
   - Includes: goals & metrics (KPI/OKR); scope; user stories with acceptance criteria; primary/alternate flows, error paths, retry/timeout rules; non-functional needs (performance, availability, security, privacy, accessibility); assumptions, constraints, dependencies, risks; test ideas/examples.

2. Architecture & Stack (`docs/architecture.md`)
   - Purpose: Explain structure and stack so teams understand construction, runtime, and operations.
   - Includes: system/module boundaries, interfaces, idempotency, concurrency; data models, schemas, migrations, caching; external APIs/integrations and authN/authZ; configuration, feature flags, secrets; observability (logs, metrics, traces, correlation IDs); runtime versions, build/test/deploy, CI/CD, release/rollback; compatibility/support policy.

3. Repo Map (`docs/repo-map.md`)
   - Purpose: Give quick orientation for AI and humans.
   - Includes: top-level structure, key directories, naming conventions; locations for configs, env, secrets, scripts, migrations, docs, ADRs; testing layout, common commands, code ownership.
   - Note: Treat the repo as the source of truth; keep the doc concise and link to folder READMEs.

Cross-cutting conventions
   - Describe only the current codebase—no future plans or ideals.
   - Start each doc with owner, status, last_updated, review_cadence.
   - Keep docs short; link to code/configs/schemas instead of duplicating.
   - Use relative links among docs.
   - Maintain `docs/glossary.md` for domain terms and abbreviations.
