"""Markdown segments: split a long prompt by headings so parts can be reused, extracted or strengthened
independently. Pure functions, no I/O. Fenced code blocks are skipped so '# comment' lines are not headings."""
import re

HEAD = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")


def split(md: str) -> list[dict]:
    heads, pos, fenced = [], 0, False
    for line in md.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            m = HEAD.match(line.rstrip("\n"))
            if m:
                heads.append({"level": len(m.group(1)), "title": m.group(2), "start": pos})
        pos += len(line)
    segs = []
    if heads and md[: heads[0]["start"]].strip():
        segs.append({"id": "s0", "level": 0, "title": "(preamble)", "start": 0, "end_own": heads[0]["start"], "end_tree": heads[0]["start"], "parent": None})
    stack = []
    for i, h in enumerate(heads):
        end_own = heads[i + 1]["start"] if i + 1 < len(heads) else len(md)
        end_tree = len(md)
        for nxt in heads[i + 1:]:
            if nxt["level"] <= h["level"]:
                end_tree = nxt["start"]
                break
        while stack and stack[-1]["level"] >= h["level"]:
            stack.pop()
        seg = {"id": f"s{i + 1}", "level": h["level"], "title": h["title"], "start": h["start"], "end_own": end_own, "end_tree": end_tree,
               "parent": stack[-1]["id"] if stack else None}
        stack.append(seg)
        segs.append(seg)
    return segs


def public(md: str) -> list[dict]:
    return [{"id": s["id"], "level": s["level"], "title": s["title"], "parent": s["parent"], "chars": s["end_tree"] - s["start"]} for s in split(md)]


def select(md: str, ids: list[str]) -> str:
    segs = {s["id"]: s for s in split(md)}
    unknown = [i for i in ids if i not in segs]
    if unknown:
        raise KeyError(unknown[0])
    spans = sorted({(segs[i]["start"], segs[i]["end_tree"]) for i in ids})
    kept = [s for s in spans if not any(o != s and o[0] <= s[0] and s[1] <= o[1] for o in spans)]  # drop nested selections
    return "\n\n".join(md[a:b].strip("\n") for a, b in kept).strip() + "\n"


def strengthen(md: str, seg_id: str, addition: str) -> str:
    """Append a rule to the end of one segment's own text (before a trailing '---' rule), leaving all else untouched."""
    segs = {s["id"]: s for s in split(md)}
    if seg_id not in segs:
        raise KeyError(seg_id)
    add = addition.strip()
    if not add:
        raise ValueError("empty addition")
    cut = segs[seg_id]["end_own"]
    head, tail = md[:cut], md[cut:]
    lines = head.rstrip("\n").split("\n")
    rule = []
    while lines and (lines[-1].strip() == "" or lines[-1].strip() in ("---", "***", "___")):
        rule.insert(0, lines.pop())
    body = "\n".join(lines)
    is_list = add.lstrip().startswith(("-", "*", "1."))
    glue = "\n" if is_list and lines and lines[-1].lstrip().startswith(("-", "*")) else "\n\n"
    return body + glue + add + "\n" + ("\n".join(rule) + "\n" if rule else "\n") + tail
