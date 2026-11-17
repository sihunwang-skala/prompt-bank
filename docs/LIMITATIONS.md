# Remaining limitations and unimplemented functionality
Not done / not verified (exact blockers in parentheses):
- **Real AI providers untested** — adapters for OpenAI/Anthropic are written but never called (no API keys here). Real token usage parsing, retries and costs are unverified. No real prices shipped (prices change; supply `RAW_PRICING_JSON`).
- **Mock model only exercised** — mock findings are heuristics (absolutes, missing sections), not AI reasoning. "Adversarial/critical/completeness" quality with real models is unknown.
- **iOS/Android apps**: `apps/mobile` is a small unbuilt scaffold (login, tasks, constraints, settings, language switch). Not installed, type-checked, run, or tested. Missing: prompts, references, history, packages, reports on mobile.
- **Web gaps**: no Playwright/E2E tests (UI was driven manually in a browser once: login → compose → run → verified result, KO/EN switch, mobile width). Task-package edit UI and rendering of package input forms (schema is validated server-side only), history date filter UI, version diff beyond the latest two, source excerpt/traceability view.
- **Validation features not built**: repeated-run statistics (success rate/variability), dataset cross-validation / held-out splits, regression *test suites* (only constraint regression between rounds), executable/source verification beyond deterministic text checks.
- **Infra**: no Redis/LangGraph/Supabase/Alembic/object storage; Postgres and multi-instance untested; retention not enforced; PDF export not implemented (Markdown only); no email/OAuth; tokens don't expire.
- **Reference discovery** only returns generic suggestions; no web retrieval. Images are stored but not sent to models.
- Semantic constraints can only be LLM-assessed → never reach `verified`.
