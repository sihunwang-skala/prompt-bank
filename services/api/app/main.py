import difflib
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select, or_
from . import config, constraints as C, history, jobs as J, reports, refs as R, security, pricing, engine as E
from .db import get_db, init_engine, now, session
from .models import *
from .providers import get_provider, parse_json, ProviderError
from .schemas import *


@asynccontextmanager
async def lifespan(app):
    init_engine()
    J.recover()
    yield
    J.reset_pool()

app = FastAPI(title="Recursive AI Workspace API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    key = request.client.host if request.client else "?"
    q, t = _hits[key], time.time()
    while q and q[0] < t - 60:
        q.popleft()
    if len(q) >= config.RATE_LIMIT_PER_MIN:
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    q.append(t)
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled(request, exc):  # never leak internals
    return JSONResponse({"detail": "internal error"}, status_code=500)


# ---------- auth ----------
def _hash(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 200_000).hex()}"


def _verify(pw, stored):
    salt, _ = stored.split("$")
    return hmac.compare_digest(_hash(pw, salt), stored)


def _th(t):
    return hashlib.sha256(t.encode()).hexdigest()


def current_user(authorization: str = Header(None), db=Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    tok = db.get(AuthToken, _th(authorization[7:]))
    if not tok:
        raise HTTPException(401, "invalid token")
    return db.get(User, tok.user_id)


def owned(db, model, id_, user):
    obj = db.get(model, id_)
    if not obj or obj.user_id != user.id:
        raise HTTPException(404, "not found")  # 404, not 403: don't reveal existence
    return obj


@app.get("/health")
def health():
    return {"ok": True, "pricing_version": pricing.PRICING_VERSION}


@app.post("/auth/register")
def register(b: Creds, db=Depends(get_db)):
    if db.scalar(select(User).where(User.email == b.email.lower())):
        raise HTTPException(409, "email already registered")
    u = User(email=b.email.lower(), password_hash=_hash(b.password), settings={"allow_external_providers": False, "default_model": "mock-1", "lang": "en"})
    db.add(u); db.commit()
    return _login_token(db, u)


def _login_token(db, u):
    tok = secrets.token_urlsafe(32)
    db.add(AuthToken(token_hash=_th(tok), user_id=u.id)); db.commit()
    return {"token": tok, "user_id": u.id}


@app.post("/auth/login")
def login(b: Creds, db=Depends(get_db)):
    u = db.scalar(select(User).where(User.email == b.email.lower()))
    if not u or not _verify(b.password, u.password_hash):
        raise HTTPException(401, "invalid credentials")
    return _login_token(db, u)


@app.get("/me")
def me(u: User = Depends(current_user)):
    return {"id": u.id, "email": u.email, "settings": u.settings}


@app.patch("/me/settings")
def set_settings(b: SettingsIn, u: User = Depends(current_user), db=Depends(get_db)):
    u.settings = {**u.settings, **b.model_dump(exclude_none=True)}
    db.commit()
    history.log(db, u.id, "settings.updated", "user", u.id, **b.model_dump(exclude_none=True))
    return u.settings


@app.delete("/me/data")
def delete_all(u: User = Depends(current_user), db=Depends(get_db)):
    """Deletes the account and everything it owns (cascade) plus uploaded files."""
    for r in db.scalars(select(Reference).where(Reference.user_id == u.id)):
        if r.storage_path:
            Path(r.storage_path).unlink(missing_ok=True)
    for model in (Job,):
        for j in db.scalars(select(Job).where(Job.user_id == u.id)):
            db.query(ValidationRound).filter_by(job_id=j.id).delete()
    for model in (ConstraintVersion,):
        for c in db.scalars(select(Constraint).where(Constraint.user_id == u.id)):
            db.query(ConstraintVersion).filter_by(constraint_id=c.id).delete()
    for p in db.scalars(select(Prompt).where(Prompt.user_id == u.id)):
        db.query(PromptVersion).filter_by(prompt_id=p.id).delete()
    for p in db.scalars(select(TaskPackage).where(TaskPackage.user_id == u.id)):
        db.query(TaskPackageVersion).filter_by(package_id=p.id).delete()
    for m in (Job, Constraint, Reference, TaskPackage, Prompt, HistoryEvent, Project, AuthToken):
        db.query(m).filter_by(user_id=u.id).delete()
    db.delete(u); db.commit()
    return {"deleted": True}


def _external_ok(u, model):
    if not model.startswith("mock-") and not u.settings.get("allow_external_providers"):
        raise HTTPException(403, "external provider use requires explicit approval in settings (your prompts/references would be sent to a third party)")


# ---------- projects ----------
@app.post("/projects")
def create_project(b: ProjectIn, u: User = Depends(current_user), db=Depends(get_db)):
    p = Project(user_id=u.id, name=b.name, description=b.description)
    db.add(p); db.commit()
    history.log(db, u.id, "project.created", "project", p.id, p.id, name=p.name)
    return _p(p)


def _p(p):
    return {"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at}


@app.get("/projects")
def list_projects(u: User = Depends(current_user), db=Depends(get_db)):
    return [_p(p) for p in db.scalars(select(Project).where(Project.user_id == u.id).order_by(Project.created_at.desc()))]


# ---------- prompts ----------
def compile_prompt(s: dict) -> str:
    titles = {"objective": "Objective", "context": "Context", "instructions": "Instructions", "constraints": "Constraints",
              "output_format": "Output Format", "references": "References", "evaluation_criteria": "Evaluation Criteria"}
    return "\n\n".join(f"## {titles[k]}\n{s[k].strip()}" for k in SECTION_KEYS if s.get(k, "").strip())


def _prompt_out(db, p, with_versions=False):
    v = db.scalar(select(PromptVersion).where(PromptVersion.prompt_id == p.id, PromptVersion.version == p.current_version))
    out = {"id": p.id, "project_id": p.project_id, "title": p.title, "tags": p.tags, "folder": p.folder, "favorite": p.favorite,
           "version": p.current_version, "sections": v.sections, "compiled": compile_prompt(v.sections), "updated_at": p.updated_at}
    if with_versions:
        out["versions"] = [{"version": x.version, "change_note": x.change_note, "created_at": x.created_at}
                           for x in db.scalars(select(PromptVersion).where(PromptVersion.prompt_id == p.id).order_by(PromptVersion.version))]
    return out


@app.post("/projects/{pid}/prompts")
def create_prompt(pid: str, b: PromptIn, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    p = Prompt(user_id=u.id, project_id=pid, title=b.title, tags=b.tags, folder=b.folder, favorite=b.favorite)
    db.add(p); db.flush()
    db.add(PromptVersion(prompt_id=p.id, version=1, sections=b.sections, change_note="created")); db.commit()
    history.log(db, u.id, "prompt.created", "prompt", p.id, pid, title=p.title)
    return _prompt_out(db, p)


@app.get("/projects/{pid}/prompts")
def search_prompts(pid: str, q: str = "", tag: str = "", folder: str = "", favorite: bool | None = None, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    out = []
    for p in db.scalars(select(Prompt).where(Prompt.user_id == u.id, Prompt.project_id == pid).order_by(Prompt.updated_at.desc())):
        if tag and tag not in p.tags or folder and p.folder != folder or favorite is not None and p.favorite != favorite:
            continue
        o = _prompt_out(db, p)
        if q and q.lower() not in (p.title + " " + o["compiled"] + " ".join(p.tags)).lower():
            continue
        out.append(o)
    return out


@app.get("/prompts/{id}")
def get_prompt(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    return _prompt_out(db, owned(db, Prompt, id, u), True)


@app.patch("/prompts/{id}")
def patch_prompt(id: str, b: PromptPatch, u: User = Depends(current_user), db=Depends(get_db)):
    p = owned(db, Prompt, id, u)
    if b.title is not None: p.title = b.title
    if b.tags is not None: p.tags = b.tags
    if b.folder is not None: p.folder = b.folder
    if b.favorite is not None: p.favorite = b.favorite
    if b.sections is not None:
        cur = db.scalar(select(PromptVersion).where(PromptVersion.prompt_id == id, PromptVersion.version == p.current_version))
        merged = {**cur.sections, **b.sections}
        if merged != cur.sections:
            p.current_version += 1
            db.add(PromptVersion(prompt_id=id, version=p.current_version, sections=merged, change_note=b.change_note or "edited"))
            history.log(db, u.id, "prompt.version", "prompt", id, p.project_id, version=p.current_version, note=b.change_note)
    db.commit()
    return _prompt_out(db, p, True)


@app.post("/prompts/{id}/duplicate")
def dup_prompt(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    p = owned(db, Prompt, id, u)
    o = _prompt_out(db, p)
    return create_prompt(p.project_id, PromptIn(title=p.title + " (copy)", sections=o["sections"], tags=p.tags, folder=p.folder), u, db)


@app.get("/prompts/{id}/diff")
def diff_prompt(id: str, a: int, b: int, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Prompt, id, u)
    va, vb = (db.scalar(select(PromptVersion).where(PromptVersion.prompt_id == id, PromptVersion.version == n)) for n in (a, b))
    if not va or not vb:
        raise HTTPException(404, "version not found")
    changes = []
    for k in SECTION_KEYS:
        x, y = va.sections.get(k, ""), vb.sections.get(k, "")
        if x != y:
            changes.append({"section": k, "status": "added" if not x else "removed" if not y else "changed",
                            "diff": "\n".join(difflib.unified_diff(x.splitlines(), y.splitlines(), f"v{a}", f"v{b}", lineterm=""))})
    return {"from": a, "to": b, "changes": changes}


@app.get("/prompts/{id}/export")
def export_prompt(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    o = _prompt_out(db, owned(db, Prompt, id, u))
    return {"format": "raw.prompt/1", "title": o["title"], "sections": o["sections"], "tags": o["tags"], "folder": o["folder"]}


@app.post("/projects/{pid}/prompts/import")
def import_prompt(pid: str, body: dict, u: User = Depends(current_user), db=Depends(get_db)):
    if body.get("format") != "raw.prompt/1":
        raise HTTPException(422, "unsupported import format")
    return create_prompt(pid, PromptIn(title=body["title"], sections=body.get("sections", {}), tags=body.get("tags", []), folder=body.get("folder", "")), u, db)


@app.post("/prompts/build")
def build_prompt(b: BuildIn, u: User = Depends(current_user)):
    _external_ok(u, b.model)
    try:
        comp = get_provider(b.model).complete("build_prompt", "Turn the request into structured prompt sections. Reply JSON {sections,questions,suggested_references}.", b.intent, {"intent": b.intent})
    except ProviderError as e:
        raise HTTPException(502, str(e))
    data = parse_json(comp.text)
    secs = {k: v for k, v in data.get("sections", {}).items() if k in SECTION_KEYS}
    return {"sections": secs, "questions": data.get("questions", []), "suggested_references": data.get("suggested_references", []),
            "note": "Suggestions only; no documents are fetched or invented. Provide the evidence yourself or attach URLs.",
            "provider": get_provider(b.model).name}


# ---------- constraints ----------
def _cd(c):
    return J.constraint_dict(c) | {"project_id": c.project_id, "source": c.source, "conflicts_with": c.conflicts_with, "created_at": c.created_at, "updated_at": c.updated_at}


def _snap(db, c, reason):
    db.add(ConstraintVersion(constraint_id=c.id, version=c.version, snapshot=J.constraint_dict(c), reason=reason))


@app.post("/constraints")
def add_constraint(b: ConstraintIn, u: User = Depends(current_user), db=Depends(get_db)):
    try:
        check = C.validate_check(b.check)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if b.project_id:
        owned(db, Project, b.project_id, u)
    c = Constraint(user_id=u.id, project_id=b.project_id, content=b.content, scope=b.scope, priority=b.priority, severity=b.severity,
                   check=check, verification_method="semantic" if check["type"] == "semantic" else "deterministic", source=b.source)
    existing = [J.constraint_dict(x) for x in db.scalars(select(Constraint).where(Constraint.user_id == u.id, Constraint.status == "active"))]
    cand = {"id": "new", "check": check}
    conflicts = C.detect_conflicts(cand, existing)
    if conflicts:  # never silently activate a contradicting rule
        c.status, c.conflicts_with = "conflicting", [x["constraint_id"] for x in conflicts]
    db.add(c); db.flush(); _snap(db, c, "created"); db.commit()
    history.log(db, u.id, "constraint.created", "constraint", c.id, b.project_id, status=c.status, content=c.content, conflicts=conflicts)
    return _cd(c) | {"conflicts": conflicts}


@app.get("/constraints")
def list_constraints(project_id: str | None = None, status: str | None = None, u: User = Depends(current_user), db=Depends(get_db)):
    q = select(Constraint).where(Constraint.user_id == u.id)
    if project_id:
        q = q.where(or_(Constraint.project_id == project_id, Constraint.project_id.is_(None)))
    if status:
        q = q.where(Constraint.status == status)
    cs = [_cd(c) for c in db.scalars(q.order_by(Constraint.created_at))]
    return {"constraints": cs, "resolution": C.resolve_effective(cs)["overridden"]}


@app.patch("/constraints/{id}")
def patch_constraint(id: str, b: ConstraintPatch, u: User = Depends(current_user), db=Depends(get_db)):
    c = owned(db, Constraint, id, u)
    changed = b.model_dump(exclude_none=True, exclude={"reason"})
    if "check" in changed:
        try:
            changed["check"] = C.validate_check(changed["check"])
        except ValueError as e:
            raise HTTPException(422, str(e))
        c.verification_method = "semantic" if changed["check"]["type"] == "semantic" else "deterministic"
    for k, v in changed.items():
        setattr(c, k, v)
    c.version += 1
    _snap(db, c, b.reason or "edited"); db.commit()  # previous versions are kept
    history.log(db, u.id, "constraint.updated", "constraint", id, c.project_id, version=c.version, changes=list(changed), reason=b.reason)
    return _cd(c)


@app.get("/constraints/{id}/versions")
def constraint_versions(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Constraint, id, u)
    return [{"version": v.version, "snapshot": v.snapshot, "reason": v.reason, "created_at": v.created_at}
            for v in db.scalars(select(ConstraintVersion).where(ConstraintVersion.constraint_id == id).order_by(ConstraintVersion.version))]


@app.post("/constraints/{id}/resolve")
def resolve_constraint(id: str, b: ResolveIn, u: User = Depends(current_user), db=Depends(get_db)):
    c = owned(db, Constraint, id, u)
    if c.status != "conflicting":
        raise HTTPException(409, "constraint is not conflicting")
    others = [db.get(Constraint, x) for x in c.conflicts_with]
    if b.action == "replace_existing":  # explicit user decision; old rules preserved as superseded
        for o in others:
            if o and o.user_id == u.id:
                o.status = "superseded"; o.version += 1; _snap(db, o, f"superseded by {c.id}")
        c.status = "active"
    elif b.action == "keep_existing":
        c.status = "disabled"
    else:
        c.status = "active"  # both active: resolve_effective applies priority, loser reported as overridden
    c.version += 1; _snap(db, c, f"resolved: {b.action}"); db.commit()
    history.log(db, u.id, "constraint.resolved", "constraint", id, c.project_id, action=b.action, conflicts=c.conflicts_with)
    return _cd(c)


# ---------- references ----------
@app.post("/projects/{pid}/references/file")
async def upload_ref(pid: str, file: UploadFile = File(...), role: str = Form("background"), u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    if role not in R.ROLES:
        raise HTTPException(422, f"role must be one of {R.ROLES}")
    name = R.safe_name(file.filename or "file")
    if Path(name).suffix.lower() not in R.ALLOWED_EXT:
        raise HTTPException(415, "file type not allowed")
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large")
    text, status, warns = R.extract(name, data)
    inj = security.scan_injection(text)
    if inj:
        warns.append("possible prompt-injection phrases detected; content is treated as untrusted data")
    path = config.data_dir() / "uploads" / f"{secrets.token_hex(12)}_{name}"
    path.write_bytes(data)
    r = Reference(user_id=u.id, project_id=pid, name=name, kind="file", mime=file.content_type or "", size=len(data), role=role,
                  storage_path=str(path), text=text, extraction=status, warnings=warns)
    db.add(r); db.commit()
    history.log(db, u.id, "reference.added", "reference", r.id, pid, name=name, role=role, extraction=status)
    return _ref(r)


@app.post("/references/url")
def add_url(b: RefUrl, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, b.project_id, u)
    if b.role not in R.ROLES:
        raise HTTPException(422, "invalid role")
    try:
        final, ctype, body = security.fetch_url(b.url)
    except (security.UnsafeURL, Exception) as e:
        raise HTTPException(422, f"URL rejected: {e}" if isinstance(e, security.UnsafeURL) else "could not fetch URL")
    import re as _re
    text = _re.sub(r"\s+", " ", _re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", body.decode("utf-8", "replace"), flags=_re.S | _re.I)).strip()
    warns = ["possible prompt-injection phrases detected; content is treated as untrusted data"] if security.scan_injection(text) else []
    r = Reference(user_id=u.id, project_id=b.project_id, name=final[:300], kind="url", source_url=final, mime=ctype[:100], size=len(body), role=b.role, text=text, warnings=warns)
    db.add(r); db.commit()
    history.log(db, u.id, "reference.added", "reference", r.id, b.project_id, url=final, role=b.role)
    return _ref(r)


def _ref(r, full=False):
    d = {"id": r.id, "project_id": r.project_id, "name": r.name, "kind": r.kind, "source_url": r.source_url, "size": r.size, "role": r.role,
         "extraction": r.extraction, "warnings": r.warnings, "preview": r.text[:400]}
    if full:
        d["text"] = r.text
    return d


@app.get("/projects/{pid}/references")
def list_refs(pid: str, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    return [_ref(r) for r in db.scalars(select(Reference).where(Reference.user_id == u.id, Reference.project_id == pid))]


@app.get("/references/{id}")
def get_ref(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    return _ref(owned(db, Reference, id, u), True)


@app.patch("/references/{id}")
def set_role(id: str, role: str, u: User = Depends(current_user), db=Depends(get_db)):
    r = owned(db, Reference, id, u)
    if role not in R.ROLES:
        raise HTTPException(422, "invalid role")
    r.role = role; db.commit()
    history.log(db, u.id, "reference.role_changed", "reference", id, r.project_id, role=role)
    return _ref(r)


@app.delete("/references/{id}")
def del_ref(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    r = owned(db, Reference, id, u)
    if r.storage_path:
        Path(r.storage_path).unlink(missing_ok=True)
    history.log(db, u.id, "reference.deleted", "reference", id, r.project_id, name=r.name)
    db.delete(r); db.commit()
    return {"deleted": True}


# ---------- jobs ----------
def _job(j, rounds=False, db=None):
    d = {"id": j.id, "project_id": j.project_id, "state": j.state, "stage": j.stage, "verification_status": j.verification_status,
         "stop_reason": j.stop_reason, "error": j.error, "estimate": j.estimate, "usage": j.usage, "config": j.config, "attempts": j.attempts,
         "created_at": j.created_at, "started_at": j.started_at, "finished_at": j.finished_at, "result": j.result, "parent_job_id": j.parent_job_id,
         "constraints_applied": j.constraint_snapshot, "prompt_text": j.prompt_text}
    if rounds:
        d["rounds"] = [{"index": r.index, "output": r.output, "stages": r.stages, "issues": r.issues, "repairs": r.repairs, "compliance": r.compliance, "cost": r.cost, "seconds": r.seconds}
                       for r in db.scalars(select(ValidationRound).where(ValidationRound.job_id == j.id).order_by(ValidationRound.index))]
    return d


@app.post("/estimate")
def estimate(b: RunIn, u: User = Depends(current_user), db=Depends(get_db)):
    return E.estimate(b.config.model_dump(), len(b.task or ""), J.avg_call_seconds(db, u.id))


@app.post("/jobs")
def run(b: RunIn, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, b.project_id, u)
    task = b.task
    if b.prompt_id:
        task = _prompt_out(db, owned(db, Prompt, b.prompt_id, u))["compiled"]
    if not task:
        raise HTTPException(422, "task or prompt_id required")
    for m in {b.config.model, b.config.reviewer_model} - {None}:
        _external_ok(u, m)
    for rid in b.config.reference_ids:
        owned(db, Reference, rid, u)
    extra = []
    for i, ec in enumerate(b.extra_constraints):
        extra.append({"id": f"exec_{i}", "content": ec.content, "scope": "execution", "priority": ec.priority, "severity": ec.severity,
                      "status": "active", "version": 1, "check": C.validate_check(ec.check), "verification_method": "deterministic"})
    return _job(J.create_job(db, u, b.project_id, task, b.config.model_dump(), b.constraint_ids, b.prompt_id, extra_constraints=extra), db=db)


@app.get("/jobs")
def list_jobs(project_id: str | None = None, state: str | None = None, u: User = Depends(current_user), db=Depends(get_db)):
    q = select(Job).where(Job.user_id == u.id)
    if project_id: q = q.where(Job.project_id == project_id)
    if state: q = q.where(Job.state == state)
    return [_job(j) for j in db.scalars(q.order_by(Job.created_at.desc()))]


@app.get("/jobs/{id}")
def get_job(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    j = owned(db, Job, id, u)
    db.refresh(j)
    return _job(j, True, db)


@app.post("/jobs/{id}/cancel")
def cancel_job(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    j = owned(db, Job, id, u)
    try:
        J.cancel(db, j)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return _job(j)


@app.post("/jobs/{id}/approve")
def approve_job(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    j = owned(db, Job, id, u)
    try:
        J.approve(db, j)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return _job(j)


@app.post("/jobs/{id}/change")
def mid_change(id: str, b: MidChange, u: User = Depends(current_user), db=Depends(get_db)):
    """New requirement while a job runs. The running job's snapshot is never mutated."""
    j = owned(db, Job, id, u)
    ec = b.constraint
    check = C.validate_check(ec.check)
    if b.mode == "apply_next":
        c = Constraint(user_id=u.id, project_id=j.project_id, content=ec.content, scope=ec.scope, priority=ec.priority, severity=ec.severity,
                       check=check, verification_method="semantic" if check["type"] == "semantic" else "deterministic")
        db.add(c); db.flush(); _snap(db, c, "added mid-execution (applies to next run)"); db.commit()
        history.log(db, u.id, "job.mid_change", "job", id, j.project_id, mode=b.mode, constraint_id=c.id)
        return {"mode": b.mode, "constraint": _cd(c), "job": _job(j)}
    extra = [{"id": "exec_mid", "content": ec.content, "scope": "execution", "priority": ec.priority, "severity": ec.severity, "status": "active",
              "version": 1, "check": check, "verification_method": "deterministic"}]
    snapshot_extra = j.constraint_snapshot
    if b.mode == "cancel_restart" and j.state not in J.TERMINAL:
        J.cancel(db, j)
    new = J.create_job(db, u, j.project_id, j.prompt_text, j.config, None, j.prompt_id, parent=j.id, extra_constraints=extra)
    history.log(db, u.id, "job.mid_change", "job", id, j.project_id, mode=b.mode, new_job=new.id)
    return {"mode": b.mode, "new_job": _job(new), "job": _job(j)}


# ---------- task packages ----------
def _pkg_body(db, u, b: PackageIn):
    p = _prompt_out(db, owned(db, Prompt, b.prompt_id, u))
    for rid in b.reference_ids:
        owned(db, Reference, rid, u)
    cons = []
    for cid in b.constraint_ids:
        cons.append(J.constraint_dict(owned(db, Constraint, cid, u)))
    return {"prompt": {"id": p["id"], "version": p["version"], "sections": p["sections"]}, "reference_ids": b.reference_ids,  # references by ID, not copies
            "form_schema": b.form_schema.model_dump(), "model_settings": b.model_settings.model_dump(), "constraints": cons,
            "evaluation_criteria": b.evaluation_criteria, "form_values": b.form_values,
            "reproducibility_note": "Model outputs are nondeterministic; this package reproduces inputs and settings, not identical outputs."}


@app.post("/packages")
def create_pkg(b: PackageIn, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, b.project_id, u)
    body = _pkg_body(db, u, b)
    pk = TaskPackage(user_id=u.id, project_id=b.project_id, name=b.name, body=body)
    db.add(pk); db.flush(); db.add(TaskPackageVersion(package_id=pk.id, version=1, body=body)); db.commit()
    history.log(db, u.id, "package.created", "package", pk.id, b.project_id, name=b.name)
    return _pk(pk)


def _pk(p):
    return {"id": p.id, "project_id": p.project_id, "name": p.name, "version": p.version, "body": p.body, "updated_at": p.updated_at}


@app.get("/projects/{pid}/packages")
def list_pkgs(pid: str, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    return [_pk(p) for p in db.scalars(select(TaskPackage).where(TaskPackage.user_id == u.id, TaskPackage.project_id == pid))]


@app.get("/packages/{id}")
def get_pkg(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    return _pk(owned(db, TaskPackage, id, u))


@app.put("/packages/{id}")
def update_pkg(id: str, b: PackageIn, u: User = Depends(current_user), db=Depends(get_db)):
    pk = owned(db, TaskPackage, id, u)
    body = _pkg_body(db, u, b)
    pk.version += 1; pk.body = body; pk.name = b.name
    db.add(TaskPackageVersion(package_id=id, version=pk.version, body=body)); db.commit()
    history.log(db, u.id, "package.updated", "package", id, pk.project_id, version=pk.version)
    return _pk(pk)


@app.get("/packages/{id}/compare")
def cmp_pkg(id: str, a: int, b: int, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, TaskPackage, id, u)
    va, vb = (db.scalar(select(TaskPackageVersion).where(TaskPackageVersion.package_id == id, TaskPackageVersion.version == n)) for n in (a, b))
    if not va or not vb:
        raise HTTPException(404, "version not found")
    return {"changed_fields": [k for k in set(va.body) | set(vb.body) if va.body.get(k) != vb.body.get(k)]}


@app.post("/packages/{id}/duplicate")
def dup_pkg(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    pk = owned(db, TaskPackage, id, u)
    n = TaskPackage(user_id=u.id, project_id=pk.project_id, name=pk.name + " (copy)", body=pk.body)
    db.add(n); db.flush(); db.add(TaskPackageVersion(package_id=n.id, version=1, body=n.body)); db.commit()
    return _pk(n)


@app.get("/packages/{id}/export")
def export_pkg(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    pk = owned(db, TaskPackage, id, u)
    return {"format": "raw.package/1", "name": pk.name, "version": pk.version, "body": pk.body}


@app.post("/projects/{pid}/packages/import")
def import_pkg(pid: str, doc: dict, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    if doc.get("format") != "raw.package/1":
        raise HTTPException(422, "unsupported import format")
    body = doc["body"]
    try:
        FormSchema(**body.get("form_schema", {"fields": []}))  # validate before it can ever be rendered
        ValidationCfg(**body.get("model_settings", {}))
    except Exception as e:
        raise HTTPException(422, f"invalid package: {str(e)[:200]}")
    body = {**body, "reference_ids": []}  # imported packages do not inherit another account's references
    body["constraints"] = []  # constraints must be re-approved by the importer
    pk = TaskPackage(user_id=u.id, project_id=pid, name=doc.get("name", "imported"), body=body)
    db.add(pk); db.flush(); db.add(TaskPackageVersion(package_id=pk.id, version=1, body=body)); db.commit()
    history.log(db, u.id, "package.imported", "package", pk.id, pid)
    return _pk(pk)


@app.post("/packages/{id}/run")
def run_pkg(id: str, u: User = Depends(current_user), db=Depends(get_db)):
    pk = owned(db, TaskPackage, id, u)
    body = pk.body
    cfg = {**body["model_settings"], "reference_ids": body.get("reference_ids", [])}
    _external_ok(u, cfg["model"])
    task = compile_prompt(body["prompt"]["sections"])
    if body.get("form_values"):
        task += "\n\n## Inputs\n" + "\n".join(f"- {k}: {v}" for k, v in body["form_values"].items())
    live = {c.id for c in db.scalars(select(Constraint).where(Constraint.user_id == u.id, Constraint.status == "active"))}
    ids = [c["id"] for c in body.get("constraints", []) if c["id"] in live]
    return _job(J.create_job(db, u, pk.project_id, task, cfg, ids, body["prompt"]["id"], package_id=pk.id), db=db)


# ---------- history & reports ----------
@app.get("/projects/{pid}/history")
def history_list(pid: str, kind: str = "", q: str = "", since: str = "", until: str = "", u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, pid, u)
    out = []
    for e in db.scalars(select(HistoryEvent).where(HistoryEvent.user_id == u.id, HistoryEvent.project_id == pid).order_by(HistoryEvent.created_at)):
        ts = e.created_at.isoformat()
        if kind and not e.kind.startswith(kind) or since and ts < since or until and ts > until or q and q.lower() not in (e.kind + str(e.data)).lower():
            continue
        out.append({"id": e.id, "kind": e.kind, "entity_type": e.entity_type, "entity_id": e.entity_id, "data": e.data, "created_at": e.created_at})
    return out


@app.post("/reports")
def make_report(b: ReportIn, u: User = Depends(current_user), db=Depends(get_db)):
    owned(db, Project, b.project_id, u)
    rtype = b.type or reports.pick_type(b.request)
    if rtype not in reports.T["en"]["title"]:
        raise HTTPException(422, "unknown report type")
    md = reports.build(db, u.id, b.project_id, rtype, b.lang, b.request)
    history.log(db, u.id, "report.generated", "report", "", b.project_id, type=rtype, request=b.request)
    return {"type": rtype, "markdown": md, "pdf": "not implemented (Markdown export only)"}


@app.get("/models")
def models():
    t = pricing.table()
    return {"models": [{"id": m, "mock": m.startswith("mock-"), "priced": m in t} for m in ["mock-1", "mock-forgetful", "mock-stubborn"]]
            + [{"id": "openai:<model-id>", "mock": False, "priced": False}, {"id": "anthropic:<model-id>", "mock": False, "priced": False}],
            "pricing_version": pricing.PRICING_VERSION}
