"""Reports are generated ONLY from stored records. Facts carry record IDs; interpretation is labeled."""
from sqlalchemy import select
from .models import HistoryEvent, Job, Constraint, ConstraintVersion, PromptVersion, Prompt

T = {
    "en": {"title": {"full": "Full History Report", "decisions": "Decision Summary", "requirements": "Requirements Report",
                     "validation": "Validation Report", "executive": "Executive Summary"},
           "facts": "Facts (from stored records)", "interp": "Interpretation (generated, not a stored fact)",
           "none": "No records.", "gen": "Generated"},
    "ko": {"title": {"full": "전체 이력 보고서", "decisions": "의사결정 요약", "requirements": "요구사항 보고서",
                     "validation": "검증 보고서", "executive": "경영 요약"},
           "facts": "사실 (저장된 기록 기준)", "interp": "해석 (생성된 내용이며 저장된 사실이 아님)",
           "none": "기록 없음.", "gen": "생성 시각"},
}
KEYWORDS = [("requirements", ["requirement", "constraint", "요구", "제약", "changed", "변경"]),
            ("validation", ["validation", "error", "issue", "unresolved", "검증", "오류", "미해결"]),
            ("decisions", ["decision", "decide", "approval", "의사결정", "결정", "승인"]),
            ("executive", ["executive", "summary of everything", "accomplished", "요약", "성과"]),
            ("full", ["history", "complete", "full", "이력", "전체"])]


def pick_type(request: str) -> str:
    r = request.lower()
    for t, words in KEYWORDS:
        if any(w in r for w in words):
            return t
    return "full"


def build(db, user_id, project_id, rtype="full", lang="en", request=""):
    L = T.get(lang, T["en"])
    evs = db.execute(select(HistoryEvent).where(HistoryEvent.user_id == user_id, HistoryEvent.project_id == project_id)
                     .order_by(HistoryEvent.created_at)).scalars().all()
    jobs = db.execute(select(Job).where(Job.user_id == user_id, Job.project_id == project_id).order_by(Job.created_at)).scalars().all()
    cons = db.execute(select(Constraint).where(Constraint.user_id == user_id, (Constraint.project_id == project_id) | (Constraint.project_id.is_(None)))).scalars().all()
    pick = {"requirements": lambda e: e.kind.startswith("constraint"),
            "validation": lambda e: e.kind.startswith(("validation", "job.finished", "job.failed")),
            "decisions": lambda e: e.kind in ("constraint.resolved", "constraint.approved", "job.approved", "job.mid_change", "constraint.created", "constraint.updated"),
            "full": lambda e: True, "executive": lambda e: e.kind in ("job.finished", "job.failed")}[rtype]
    sel = [e for e in evs if pick(e)]
    md = [f"# {L['title'][rtype]}", f"_{L['gen']}: {sel[-1].created_at.isoformat() if sel else '-'}_" if False else "", f"## {L['facts']}"]
    if rtype in ("requirements", "full", "decisions"):
        md.append("\n### Constraints" if lang == "en" else "\n### 제약")
        for c in cons:
            md.append(f"- `{c.id}` v{c.version} [{c.status}] ({c.scope}, p{c.priority}, {c.severity}): {c.content}")
    if rtype in ("validation", "executive", "full"):
        md.append("\n### Jobs")
        for j in jobs:
            u = j.usage or {}
            md.append(f"- `{j.id}` {j.state} / verification: **{j.verification_status or 'n/a'}** / stop: {j.stop_reason or '-'} / "
                      f"calls {u.get('calls', 0)} / cost {u.get('cost', 'n/a')}{'' if u.get('cost_complete', True) else ' (incomplete)'} / {u.get('elapsed_seconds', 'n/a')}s")
    md.append("\n### Timeline")
    md += [f"- {e.created_at.isoformat(timespec='seconds')} `{e.id}` **{e.kind}** {e.entity_id} {e.data}" for e in sel] or [L["none"]]
    open_issues = []
    for j in jobs:
        if j.verification_status in ("failed", "requires_human_review", "partially_verified", "unverified") and j.state != "CANCELLED":
            open_issues.append(f"`{j.id}`: {j.verification_status}")
    md += ["", f"## {L['interp']}",
           (f"- {len(jobs)} job(s); not fully verified: {', '.join(open_issues) or 'none'}." if lang == "en"
            else f"- 작업 {len(jobs)}건; 완전 검증되지 않음: {', '.join(open_issues) or '없음'}.")]
    if request:
        md.append(f"\n> request: {request}")
    return "\n".join(x for x in md if x != "") + "\n"
