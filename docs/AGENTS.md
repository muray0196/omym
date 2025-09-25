# docs/ for AI coding assistants

Goal: Provide a minimal, high-signal document set. Prefer machine‑readable contracts over prose. Consolidate the previous six documents into three core docs (+ optional UI guide).

1. Spec & Flows (`docs/spec.md`)
- Purpose: Unify PRD and Tool Flow. Define what to build and how it behaves.
- Includes:
  - Goals and success metrics (KPI/OKR)
  - In-scope / out-of-scope
  - User stories with acceptance criteria
  - Primary/alternate flows, error paths, retry/timeout rules
  - Non-functional requirements: performance, availability, security, privacy, accessibility
  - Assumptions, constraints, dependencies, risks
  - Test ideas / examples

2. Architecture & Stack (`docs/architecture.md`)
- Purpose: Unify Tool Logic Structure and Tech Stack. Define how it is built, runs, and is operated.
- Includes:
  - System and module boundaries; interfaces; idempotency; concurrency model
  - Data model and schemas; migrations; caching strategy
  - External APIs/integrations; authentication/authorization model
  - Configuration, feature flags, secrets management
  - Observability: logs, metrics, traces; correlation IDs
  - Runtime versions; build/test/deploy; CI/CD; release/rollback
  - Compatibility/support policy

3. Repo Map (`docs/repo-map.md`)
- Purpose: Quick orientation for AI and humans.
- Includes:
   - Top-level structure; key directories; naming conventions
   - Where configs, env, secrets, scripts, migrations, docs, ADRs live
   - Testing layout; common commands; code ownership
- Note: The repository is the source of truth; keep this doc concise and link to folder READMEs.

Cross‑cutting conventions
- Document the current codebase only: describe the system as it exists now, not plans, ideals, or future work.
- Each doc starts with: owner, status, last_updated, review_cadence
- Keep documents short; link to code/configs/schemas instead of duplicating
- Use relative links between docs
- Maintain `docs/glossary.md` for domain terms and abbreviations