# Requirements registry
Status: ✅ implemented+tested · 🟡 partial · ❌ not implemented.
| # | Requirement | Status |
|---|---|---|
| A | Recursive validation (stages, loop control, honest statuses, evidence persisted) | ✅ (mock-tested); repeated-run stats, cross-validation ❌ |
| B | Persistent constraints: registry, versions, conflicts, priority, deterministic enforcement, UI | ✅ |
| C | Prompt generation/library/versions/diff/import/export | ✅ (generation is a mock template) |
| D | References: upload/URL, roles, injection defense, SSRF | 🟡 no library re-attach UI, no excerpt traceability, no real discovery |
| E | Task packages | 🟡 API complete; limited UI |
| F | Non-blocking workspace, queue, cancel, recovery, mid-run changes | ✅ web; mobile ❌ |
| G | Per-response cost/time transparency | ✅ |
| H | History & reports | 🟡 Markdown only; no PDF |
| Platforms | Web ✅ · iOS/Android ❌ (unbuilt scaffold) |
| i18n | EN/KO with language switch at top | ✅ web, 🟡 mobile (scaffold) |
| License | PolyForm Noncommercial 1.0.0 displayed in README, app | ✅ |
