# Test report (what actually ran)
Run on macOS, Python 3.11.15, Node 24.
| Suite | Command | Result |
|---|---|---|
| Backend (pytest) | `npm run test:api` | **54 passed** |
| Web shared/i18n (vitest) | `npm run test:web` | **7 passed** (EN/KO key parity, formatting never invents numbers) |
| Web typecheck + production build | `npm run typecheck -w apps/web`, `npm run build:web` | passed |
| Manual browser check | Built web + API; login, constraints, compose, estimate, run, verified result with round-2 repair; EN/KO switch; mobile 375px layout | observed working |

Backend coverage (incl. segments: split/extract/compose/strengthen/segment-scoped run, example install): isolation, auth, constraint versions/conflicts/priority, deterministic checks, forgotten-instruction repair, unsupported-claim detection, no-improvement stop, hard iteration cap, semantic-only never `verified`, critical semantic → human review, regression, cost math + unpriced → None, budget block, approval gate, cancellation mid-run, restart recovery, mid-run changes (apply-next/branch) leave the running job untouched, prompt versions/diff/search/import/export, uploads (types/size/roles/injection warning), SSRF blocks, untrusted fencing/redaction, reference evidence cap, task packages, form-schema rejection, reports EN/KO, history filters, data deletion, rate limit.

**Written but not executed:** nothing in the repo is knowingly unexecuted except `apps/mobile` (never built) and the OpenAI/Anthropic adapters (never called).
