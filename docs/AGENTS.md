# docs/ for AI coding assistants

Goal: Provide a minimal, high-signal document set that an AI engineer can use to implement and maintain the project. Prefer machine‑readable contracts over prose. Consolidate the previous six documents into three core docs (+ optional UI guide).

1. Spec & Flows (`docs/spec.md`)
   * Purpose: Unify PRD and Tool Flow. Define what to build and how it behaves.
   * Includes:
     * Goals and success metrics (KPI/OKR)
     * In-scope / out-of-scope
     * User stories with acceptance criteria
     * Primary/alternate flows, error paths, retry/timeout rules
     * Non-functional requirements: performance, availability, security, privacy, accessibility
     * Assumptions, constraints, dependencies, risks
     * Test ideas / examples
   * Format: Use Mermaid for diagrams (user flows, state/sequence). Store sources under `docs/diagrams/`.

2. Architecture & Stack (`docs/architecture.md`)
   * Purpose: Unify Tool Logic Structure and Tech Stack. Define how it is built, runs, and is operated.
   * Includes:
     * System and module boundaries; interfaces; idempotency; concurrency model
     * Data model and schemas; migrations; caching strategy
     * External APIs/integrations; authentication/authorization model
     * Configuration, feature flags, secrets management
     * Observability: logs, metrics, traces; correlation IDs
     * Runtime versions; build/test/deploy; CI/CD; release/rollback
     * Compatibility/support policy

3. Repo Map (`docs/repo-map.md`)
   * Purpose: Quick orientation for AI and humans.
   * Includes:
     * Top-level structure; key directories; naming conventions
     * Where configs, env, secrets, scripts, migrations, docs, ADRs live
     * Testing layout; common commands; code ownership
   * Note: The repository is the source of truth; keep this doc concise and link to folder READMEs.

Optional: UI Guidelines (`docs/ui-guidelines.md`)
   * Include when UI is significant; otherwise add brief guidance in Spec.
   * Includes: Design tokens, components, patterns; accessibility (WCAG), responsiveness, i18n/l10n, motion.

Machine‑readable assets (strongly recommended)
   * CI/CD: `.github/workflows/*.yml` or equivalent
   * Diagrams: `docs/diagrams/` (Mermaid/PlantUML sources)

Cross‑cutting conventions
   * Document the current codebase only: describe the system as it exists now, not plans, ideals, or future work. Put plans in roadmaps/issues, and decisions in ADRs.
   * Each doc starts with: owner, status, last_updated, review_cadence
   * Keep documents short; link to code/configs/schemas instead of duplicating
   * Use relative links between docs
   * Maintain `docs/glossary.md` for domain terms and abbreviations

Maintenance policy
   * Update docs with functional changes; automate generation where possible
   * Use PR checklists to ensure spec/architecture are updated alongside code
