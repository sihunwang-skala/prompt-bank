"""Constraint registry logic: deterministic checks, conflict detection, priority resolution.

Deterministic checks give real pass/fail. Anything else is 'semantic' and is never reported as
verified by this module (it returns status 'unchecked' and the engine routes it to review).
"""
import json
import re

SCOPE_RANK = {"global": 0, "project": 1, "task_package": 2, "execution": 3}  # narrower = higher
CHECK_TYPES = {"required_section", "must_include", "forbidden", "exact_string", "max_chars", "min_chars", "json_keys", "semantic"}
SEVERITIES = ("critical", "major", "minor")
STATUSES = ("active", "superseded", "disabled", "conflicting", "pending_approval")


def validate_check(check: dict) -> dict:
    t = (check or {}).get("type", "semantic")
    if t not in CHECK_TYPES:
        raise ValueError(f"unknown check type: {t}")
    if t in ("required_section", "must_include", "forbidden", "exact_string") and not str(check.get("text", check.get("name", ""))).strip():
        raise ValueError("check needs non-empty 'text'")
    if t in ("max_chars", "min_chars") and not isinstance(check.get("value"), int):
        raise ValueError("check needs integer 'value'")
    if t == "json_keys" and not isinstance(check.get("keys"), list):
        raise ValueError("json_keys needs 'keys' list")
    return {"type": t, **{k: v for k, v in check.items() if k != "type"}}


def _text(check):
    return str(check.get("text", check.get("name", ""))).strip()


def _has_section(output: str, name: str) -> bool:
    pat = re.compile(r"^\s*(#{1,6}\s*|\*\*)?[^\n]*" + re.escape(name) + r"[^\n]*$", re.I | re.M)
    for m in pat.finditer(output):
        line = m.group(0).strip()
        if line.startswith("#") or line.startswith("**") or line.rstrip(":").lower() == name.lower():
            return True
    return False


def evaluate(constraint: dict, output: str) -> dict:
    """constraint: dict with id, check, severity, content. Returns a compliance record."""
    check = constraint.get("check") or {"type": "semantic"}
    t = check.get("type", "semantic")
    ok, detail = None, ""
    if t == "required_section":
        ok = _has_section(output, _text(check)); detail = f"section '{_text(check)}' {'found' if ok else 'missing'}"
    elif t == "must_include":
        ok = _text(check).lower() in output.lower(); detail = f"text '{_text(check)}' {'found' if ok else 'missing'}"
    elif t == "exact_string":
        ok = _text(check) in output; detail = f"exact string {'found' if ok else 'missing'}"
    elif t == "forbidden":
        ok = _text(check).lower() not in output.lower(); detail = f"forbidden text '{_text(check)}' {'absent' if ok else 'present'}"
    elif t == "max_chars":
        ok = len(output) <= check["value"]; detail = f"{len(output)} chars (max {check['value']})"
    elif t == "min_chars":
        ok = len(output) >= check["value"]; detail = f"{len(output)} chars (min {check['value']})"
    elif t == "json_keys":
        try:
            data = json.loads(output)
            miss = [k for k in check["keys"] if not isinstance(data, dict) or k not in data]
            ok = not miss; detail = "all keys present" if ok else f"missing keys: {miss}"
        except Exception:
            ok = False; detail = "output is not valid JSON"
    status = "unchecked" if ok is None else ("pass" if ok else "fail")
    return {"constraint_id": constraint["id"], "status": status, "method": "semantic" if ok is None else "deterministic",
            "severity": constraint.get("severity", "major"), "detail": detail or "requires semantic/human review",
            "content": constraint.get("content", "")}


def _conflict(a: dict, b: dict) -> str | None:
    ta, tb = a.get("type"), b.get("type")
    for x, y in ((a, b), (b, a)):
        if x.get("type") in ("required_section", "must_include", "exact_string") and y.get("type") == "forbidden":
            p, q = _text(x).lower(), _text(y).lower()
            if p and q and (p in q or q in p):
                return f"'{_text(x)}' is required but '{_text(y)}' is forbidden"
    if {ta, tb} == {"max_chars", "min_chars"}:
        mx, mn = (a, b) if ta == "max_chars" else (b, a)
        if mx["value"] < mn["value"]:
            return f"max_chars {mx['value']} < min_chars {mn['value']}"
    return None


def detect_conflicts(candidate: dict, existing: list[dict]) -> list[dict]:
    """Return existing active constraints that contradict candidate (dicts with id, check)."""
    out = []
    for e in existing:
        if e["id"] == candidate.get("id") or e.get("status", "active") != "active":
            continue
        why = _conflict(candidate["check"], e["check"])
        if why:
            out.append({"constraint_id": e["id"], "reason": why})
    return out


def resolve_effective(constraints: list[dict]) -> dict:
    """Pick the effective set. Priority first, then narrower scope. Losers are reported, never deleted."""
    active = [c for c in constraints if c.get("status") == "active"]
    key = lambda c: (c["priority"], SCOPE_RANK.get(c["scope"], 0))
    overridden, losers = [], set()
    for i, a in enumerate(active):
        for b in active[i + 1:]:
            why = _conflict(a["check"], b["check"])
            if why:
                win, lose = (a, b) if key(a) >= key(b) else (b, a)
                losers.add(lose["id"])
                overridden.append({"constraint_id": lose["id"], "overridden_by": win["id"], "reason": why})
    effective = sorted((c for c in active if c["id"] not in losers), key=key, reverse=True)
    return {"effective": effective, "overridden": overridden}
