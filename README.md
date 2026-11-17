**English** · [한국어](README.ko.md)

# Prompt Bank

An AI prompt workspace built around two ideas: **recursive validation** of AI output, and **persistent instruction enforcement** so earlier rules are not silently forgotten. Results are labeled *Verified / Partially verified / Unverified / Failed / Requires human review* with the evidence stored, and every run shows its recorded cost and time.

> **Status: working MVP foundation, not a finished product.** The backend, web app and the validation engine run and are tested against an **offline mock model**. Real OpenAI/Anthropic adapters exist but are **untested** (no credentials were available). The mobile app is an **unbuilt scaffold**. See [Limitations](docs/LIMITATIONS.md) and the [test report](docs/TEST_REPORT.md) for exactly what is and isn't verified.

## License

**PolyForm Noncommercial License 1.0.0** — Copyright © 2026 Sihun Wang. See [LICENSE](LICENSE).

- ✅ Free for personal, research, educational and other noncommercial use.
- ❌ Commercial use or resale requires prior written permission from the author.
- This is a *source-available* license, not an OSI-approved open-source license.
- The license covers this project's code and docs only; it grants no rights to third-party names or services (OpenAI, Anthropic, …). Not affiliated with or endorsed by them.
- Provided "as is", without warranty.

The license is also shown in the app (login screen, footer, Settings).

## What works (verified by automated tests)

| Area | Implemented |
|---|---|
| Recursive validation | generate → critical / completeness / adversarial review (by depth) → constraint compliance → evidence check → regression check → repair → re-evaluate; hard caps on rounds, cost, time; stops on pass / no improvement / limits / cancel |
| Constraint registry | scopes, priority, severity, versions, conflict detection (never silent), supersede/disable, per-round deterministic checks |
| Honest statuses | `verified` needs ≥1 deterministic check passing; semantic-only constraints never reach `verified` |
| Jobs | persistent queue, approval gate, cancel, restart recovery, mid-run change (apply-next / cancel-restart / branch) without mutating the running job |
| Cost & time | per-job calls, retries, tokens, cost, elapsed; versioned pricing; unknown price → "unavailable", never invented |
| Prompts & packages | structured sections, versions, diff, search, tags, favorites, import/export; task packages (versions, compare, duplicate, run, export/import) |
| References | upload (type/size limits), URL import with SSRF guard, roles, prompt-injection screening, untrusted-data fencing |
| History & reports | structured event log; Markdown reports (EN/KO) generated only from stored records |
| UI | Web (EN/KO language switch at top), responsive, non-blocking side panel + queue |

## Quick start

Requirements: Python 3.11+, Node 20+.

```bash
python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt
npm install
npm run api        # API on http://localhost:8000
npm run web        # Web on http://localhost:3000  (second terminal)
```

Open http://localhost:3000, create an account, create a project, add a constraint, then **Compose → Execute**. The default model `mock-1` needs no keys. Try `mock-forgetful` (forgets constraints until the validator catches it) and `mock-stubborn` (never improves, to see the stop rules).

Tests:
```bash
npm run test:api   # 44 backend tests
npm run test:web   # 7 shared/i18n tests
```

Real providers: copy `.env.example`, set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` **on the server**, supply real prices in `RAW_PRICING_JSON`, then enable external providers in Settings and use model ids `openai:<id>` / `anthropic:<id>`.

## Screenshots

Captured from the running app with the offline mock model and demo data (`scripts/screenshots.py`).

**Login (language switch + license)**

![Login (language switch + license)](docs/screenshots/01-login.png)

**Home: running tasks, recent tasks, packages, prompts**

![Home: running tasks, recent tasks, packages, prompts](docs/screenshots/02-home.png)

**Prompt composer: structured sections, references, validation depth, cost/time estimate**

![Prompt composer: structured sections, references, validation depth, cost/time estimate](docs/screenshots/03-compose.png)

**Recursive validation: issues, repairs, constraint compliance per round, cost and time**

![Recursive validation: issues, repairs, constraint compliance per round, cost and time](docs/screenshots/04-validation.png)

**Constraint registry with a detected conflict awaiting your decision**

![Constraint registry with a detected conflict awaiting your decision](docs/screenshots/05-constraints.png)

**Library: search, favorites, version compare, task packages**

![Library: search, favorites, version compare, task packages](docs/screenshots/06-library.png)

**References: roles, previews, prompt-injection warning**

![References: roles, previews, prompt-injection warning](docs/screenshots/07-references.png)

**History & on-demand reports (generated only from stored records)**

![History & on-demand reports (generated only from stored records)](docs/screenshots/08-history-reports.png)

**Settings: external-provider consent, retention, license, data deletion**

![Settings: external-provider consent, retention, license, data deletion](docs/screenshots/09-settings.png)

**Korean UI**

![Korean UI](docs/screenshots/10-korean-validation.png)

**Mobile-width web (bottom tabs)**

![Mobile-width web (bottom tabs)](docs/screenshots/11-mobile-web-home.png)


## Docs
[Architecture](docs/ARCHITECTURE.md) · [Requirements registry](docs/REQUIREMENTS.md) · [Security](docs/SECURITY.md) · [Deployment](docs/DEPLOYMENT.md) · [Test report](docs/TEST_REPORT.md) · [Limitations](docs/LIMITATIONS.md)
