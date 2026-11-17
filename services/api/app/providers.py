"""Model provider adapters. Business logic only sees Provider.complete().

- Mock providers are OFFLINE, deterministic and clearly labeled; they simulate model behaviour for
  development/tests (mock-1 follows constraints; mock-forgetful forgets them until reminded;
  mock-stubborn never improves). They are NOT AI and their findings are heuristics.
- OpenAI / Anthropic adapters are implemented against the public HTTP APIs but are UNTESTED here
  (no credentials in the build environment). See docs/LIMITATIONS.md.
"""
import json
import re
import time
from dataclasses import dataclass, field
import httpx
from . import config


@dataclass
class Completion:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int = 0
    usage_source: str = "unavailable"  # provider | estimated | unavailable
    retries: int = 0
    raw_meta: dict = field(default_factory=dict)


class ProviderError(Exception):
    pass


class Provider:
    name = "base"
    is_external = False

    def complete(self, kind: str, system: str, user: str, meta: dict | None = None) -> Completion:
        raise NotImplementedError


def _est(text: str) -> int:
    return max(1, len(text) // 4)


ABSOLUTES = re.compile(r"\b(always correct|guaranteed to work|always|guaranteed|100%|never fails)\b", re.I)
SWAP = {"always correct": "usually correct", "guaranteed to work": "expected to work", "always": "typically",
        "guaranteed": "expected", "100%": "most", "never fails": "rarely fails"}


class MockProvider(Provider):
    is_external = False

    def __init__(self, model: str = "mock-1"):
        self.model = model
        self.name = f"mock:{model}"

    # -- helpers -----------------------------------------------------------------
    def _apply_constraints(self, out: str, checks: list[dict]) -> str:
        for c in checks:
            t = c.get("type")
            text = str(c.get("text", c.get("name", ""))).strip()
            if t == "required_section" and text.lower() not in out.lower():
                out += f"\n\n## {text}\nContent for {text} (mock placeholder)."
            elif t in ("must_include", "exact_string") and text.lower() not in out.lower():
                out += f"\n\n{text}"
            elif t == "forbidden" and text:
                out = re.sub(re.escape(text), "[removed]", out, flags=re.I)
        for c in checks:
            if c.get("type") == "max_chars" and len(out) > c["value"]:
                out = out[: c["value"]]
            if c.get("type") == "min_chars" and len(out) < c["value"]:
                out += " " + ("Additional detail. " * ((c["value"] - len(out)) // 18 + 1))
        return out

    def _generate(self, meta):
        task = next((l.strip("# ").strip() for l in meta.get("task", "").split("\n") if l.strip() and not l.startswith("#")), meta.get("task", "")[:80])
        out = (f"# Result\n\n## Summary\nDraft response for: {task[:80]}.\n\n"
               "## Analysis\nThis approach is always correct and guaranteed to work.\n")
        honors = self.model == "mock-1" or meta.get("reminded")
        if honors:
            out = self._apply_constraints(out, meta.get("constraints", []))
        return out

    def _repair(self, meta):
        out = meta.get("output", "")
        if self.model == "mock-stubborn":
            return out
        out = ABSOLUTES.sub(lambda m: SWAP.get(m.group(0).lower(), "usually"), out)
        return self._apply_constraints(out, meta.get("constraints", []))

    def _review(self, kind, meta):
        out, findings = meta.get("output", ""), []
        if kind == "review_critical":
            if not out.strip():
                findings.append(dict(severity="critical", category="empty_output", description="Output is empty.", necessary=True))
            for m in ABSOLUTES.finditer(out):
                findings.append(dict(severity="major", category="unsupported_generalization", necessary=True,
                                     description=f"Unsupported absolute claim: '{m.group(0)}'.", evidence=out[max(0, m.start() - 30): m.end() + 30]))
                break
        elif kind == "review_adversarial":
            if not re.search(r"risk|limitation|counter|fail|리스크|한계|반론", out, re.I):
                findings.append(dict(severity="minor", category="no_failure_modes", necessary=False,
                                     description="No failure modes or counterarguments are discussed."))
        elif kind == "review_completeness":
            for s in meta.get("sections", []):
                if s.lower() not in out.lower():
                    findings.append(dict(severity="major", category="missing_requirement", necessary=True,
                                         description=f"Required section '{s}' is missing."))
            if len(meta.get("task", "").split()) < 4:
                findings.append(dict(severity="minor", category="underspecified_task", necessary=False,
                                     description="The task is brief; consider specifying audience and format."))
        for f in findings:
            f["source"] = "mock-heuristic"
        return json.dumps({"findings": findings})

    def _build_prompt(self, meta):
        intent = meta.get("intent", "")
        questions = []
        if len(intent.split()) < 4:
            questions.append("Who is the audience and what output format do you need?")
        return json.dumps({
            "sections": {
                "objective": intent.strip(),
                "context": "",
                "instructions": "Address the objective directly. State assumptions. Note risks and limitations.",
                "constraints": "",
                "output_format": "Sections: Summary, Analysis",
                "references": "",
                "evaluation_criteria": "Complete; consistent with constraints; claims are supported.",
            },
            "questions": questions,
            "suggested_references": ["Primary sources relevant to the task", "Your own data or documents"],
            "source": "mock-template",
        })

    def complete(self, kind, system, user, meta=None):
        meta = meta or {}
        text = {"generate": lambda: self._generate(meta), "repair": lambda: self._repair(meta),
                "build_prompt": lambda: self._build_prompt(meta),
                "review_constraints": lambda: json.dumps({"verdicts": [
                    {"constraint_id": cid, "verdict": "uncertain", "note": "mock cannot assess semantic constraints"}
                    for cid in meta.get("semantic_ids", [])]})}.get(kind, lambda: self._review(kind, meta))()
        return Completion(text, _est(system + user), _est(text), 0, "estimated")


class _HttpProvider(Provider):
    is_external = True
    max_retries = 2

    def _post(self, url, headers, body):
        retries = 0
        while True:
            try:
                r = httpx.post(url, headers=headers, json=body, timeout=120)
                if r.status_code in (429, 500, 502, 503, 529) and retries < self.max_retries:
                    retries += 1
                    time.sleep(min(2 ** retries, 8))
                    continue
                r.raise_for_status()
                return r.json(), retries
            except httpx.HTTPError as e:
                if retries < self.max_retries and not isinstance(e, httpx.HTTPStatusError):
                    retries += 1
                    time.sleep(1)
                    continue
                raise ProviderError(f"{self.name} request failed: {type(e).__name__}")


class OpenAIProvider(_HttpProvider):
    def __init__(self, model):
        self.model, self.name = model, f"openai:{model}"

    def complete(self, kind, system, user, meta=None):
        if not config.OPENAI_API_KEY:
            raise ProviderError("OPENAI_API_KEY is not set on the server")
        data, retries = self._post("https://api.openai.com/v1/chat/completions",
                                   {"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                                   {"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        u = data.get("usage") or {}
        return Completion(data["choices"][0]["message"]["content"], u.get("prompt_tokens"), u.get("completion_tokens"),
                          (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0), "provider" if u else "unavailable", retries)


class AnthropicProvider(_HttpProvider):
    def __init__(self, model):
        self.model, self.name = model, f"anthropic:{model}"

    def complete(self, kind, system, user, meta=None):
        if not config.ANTHROPIC_API_KEY:
            raise ProviderError("ANTHROPIC_API_KEY is not set on the server")
        data, retries = self._post("https://api.anthropic.com/v1/messages",
                                   {"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                                   {"model": self.model, "max_tokens": 4096, "system": system, "messages": [{"role": "user", "content": user}]})
        u = data.get("usage") or {}
        text = "".join(b.get("text", "") for b in data.get("content", []))
        return Completion(text, u.get("input_tokens"), u.get("output_tokens"), u.get("cache_read_input_tokens", 0),
                          "provider" if u else "unavailable", retries)


def get_provider(model: str) -> Provider:
    if model.startswith("mock-"):
        return MockProvider(model)
    if model.startswith("openai:"):
        return OpenAIProvider(model.split(":", 1)[1])
    if model.startswith("anthropic:"):
        return AnthropicProvider(model.split(":", 1)[1])
    raise ProviderError(f"unknown model '{model}' (use mock-1, openai:<id>, anthropic:<id>)")


def parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}
