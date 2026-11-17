# Architecture

```
apps/web (Next.js, TS)   apps/mobile (Expo scaffold, unbuilt)
          \                 /
        packages/shared  (API client, i18n EN/KO, status helpers)
                |  HTTP/JSON
        services/api  (FastAPI)
          main.py       routes, auth, rate limit, isolation
          engine.py     bounded recursive validation
          constraints.py deterministic checks, conflicts, priority
          jobs.py       persistent queue + in-process workers
          providers.py  mock + OpenAI + Anthropic adapters
          pricing.py    versioned pricing (no invented prices)
          security.py   SSRF guard, injection screening, redaction
          reports.py    reports from stored events only
          SQLAlchemy -> SQLite (default) / PostgreSQL URL
```

## Decisions (deviations from the brief, with reasons)
- **Worker in the API process** (thread pool) instead of a separate `services/worker` + Redis. All job state is in the DB, so `run_job()` can move to a separate process/queue later. Lower cost and complexity for individual use. Recovery on restart is implemented and tested.
- **SQLite default**, Postgres by URL (untested). **`create_all`**, no Alembic migrations yet.
- **Own simple auth** (PBKDF2 + opaque bearer tokens) instead of Supabase Auth, to stay dependency-free. Tokens have no expiry yet.
- **No LangGraph.** A plain bounded loop is simpler and fully testable; per-round persistence gives checkpoints.
- **No Tailwind**; plain CSS to keep dependencies minimal.

## Validation engine
Each round: reviews (by depth: quick=critical; standard=+completeness; deep=+adversarial) → deterministic constraint checks (semantic ones are only LLM-assessed and never "verified") → evidence check → regression (previously passing constraint now failing) → repair. Stops on: all checks pass, no improvement, max rounds (hard cap 10), budget, time, cancel, provider error. Budget/time/cancel are checked **before** every provider call.

Final status: `verified` (blocking issues none, ≥1 deterministic check passed, no semantic/evidence gaps) · `partially_verified` · `unverified` (stopped before checks completed) · `failed` (blocking issues remain) · `requires_human_review` (critical semantic constraint).

## Data model
users, auth_tokens, projects, prompts/prompt_versions, constraints/constraint_versions, references, task_packages/versions, jobs (frozen config + constraint snapshot), validation_rounds, history_events. Every row is scoped by `user_id`; other users' ids return 404.
