"""Versioned pricing. We do NOT ship real provider prices (they change and we won't guess them).
Supply real prices via RAW_PRICING_JSON='{"model-id": {"in": usd_per_Mtok, "out": ..., "cached_in": ...}}'.
Models without a price yield cost=None ('unavailable')."""
import json
import os

PRICING_VERSION = "2026-11-18"
_BUILTIN = {  # illustrative, labeled as such; only for the offline mock providers
    "mock-1": {"in": 1.0, "out": 3.0, "cached_in": 0.1, "illustrative": True},
    "mock-forgetful": {"in": 1.0, "out": 3.0, "cached_in": 0.1, "illustrative": True},
    "mock-stubborn": {"in": 1.0, "out": 3.0, "cached_in": 0.1, "illustrative": True},
}


def table() -> dict:
    t = dict(_BUILTIN)
    extra = os.environ.get("RAW_PRICING_JSON")
    if extra:
        t.update(json.loads(extra))
    return t


def cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float | None:
    p = table().get(model)
    if not p:
        return None
    fresh = max(input_tokens - cached_tokens, 0)
    return (fresh * p["in"] + cached_tokens * p.get("cached_in", p["in"]) + output_tokens * p["out"]) / 1_000_000
