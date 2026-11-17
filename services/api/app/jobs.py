"""Persistent job queue. States: QUEUED RUNNING WAITING_FOR_APPROVAL COMPLETED FAILED CANCELLED.
All state lives in the DB, so a restart can recover: RUNNING jobs are re-queued (attempt counted)
by recover(). Worker = threads in the API process (low cost); the same run_job() can be driven from
a separate worker process / Redis queue later without code changes."""
import threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from . import config, constraints as C, engine as E, history
from .db import session, now
from .models import Job, ValidationRound, Constraint, Reference
from .security import wrap_untrusted

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
MAX_ATTEMPTS = 3
_pool = None
_lock = threading.Lock()


def pool():
    global _pool
    with _lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=config.WORKER_THREADS, thread_name_prefix="raw-worker")
        return _pool


def reset_pool():
    global _pool
    if _pool:
        _pool.shutdown(wait=True)
    _pool = None


def constraint_dict(c: Constraint) -> dict:
    return dict(id=c.id, content=c.content, scope=c.scope, priority=c.priority, severity=c.severity, status=c.status,
                version=c.version, check=c.check, verification_method=c.verification_method)


def avg_call_seconds(db, user_id):
    rows = db.execute(select(Job.usage).where(Job.user_id == user_id, Job.state == "COMPLETED").order_by(Job.finished_at.desc()).limit(20)).scalars().all()
    v = [u.get("avg_call_seconds") for u in rows if u and u.get("avg_call_seconds")]
    return sum(v) / len(v) if v else None


def create_job(db, user, project_id, task_text, cfg, constraint_ids=None, prompt_id=None, package_id=None, parent=None, extra_constraints=None):
    """Freezes config + constraint snapshot at creation: a running job is never mutated by later edits."""
    cfg = E.normalize_config(cfg)
    q = select(Constraint).where(Constraint.user_id == user.id, Constraint.status == "active",
                                 (Constraint.project_id == project_id) | (Constraint.project_id.is_(None)))
    cons = [constraint_dict(c) for c in db.execute(q).scalars()
            if constraint_ids is None or c.id in constraint_ids or c.scope == "global"]
    cons += extra_constraints or []
    est = E.estimate(cfg, len(task_text), avg_call_seconds(db, user.id))
    needs = None
    if cfg["max_cost"] is not None and not est["price_known"]:
        needs = "price_unknown_budget_unenforceable"
    elif cfg["max_cost"] is not None and est["cost_low"] is not None and est["cost_low"] > cfg["max_cost"]:
        needs = "estimate_exceeds_budget"
    job = Job(user_id=user.id, project_id=project_id, prompt_id=prompt_id, package_id=package_id, parent_job_id=parent,
              state="WAITING_FOR_APPROVAL" if needs else "QUEUED", config=cfg, constraint_snapshot=cons, prompt_text=task_text,
              estimate={**est, "approval_reason": needs})
    db.add(job)
    db.commit()
    history.log(db, user.id, "job.created", "job", job.id, project_id, state=job.state, config=cfg, model=cfg["model"], approval_reason=needs)
    if not needs:
        submit(job.id)
    return job


def submit(job_id):
    pool().submit(run_job, job_id)


def approve(db, job: Job):
    if job.state != "WAITING_FOR_APPROVAL":
        raise ValueError("job is not waiting for approval")
    job.approved, job.state = True, "QUEUED"
    db.commit()
    history.log(db, job.user_id, "job.approved", "job", job.id, job.project_id)
    submit(job.id)


def cancel(db, job: Job):
    if job.state in TERMINAL:
        raise ValueError("job already finished")
    job.cancel_requested = True
    if job.state in ("QUEUED", "WAITING_FOR_APPROVAL"):
        job.state, job.finished_at, job.verification_status = "CANCELLED", now(), "unverified"
        job.stop_reason = "cancelled"
    db.commit()
    history.log(db, job.user_id, "job.cancel_requested", "job", job.id, job.project_id, state=job.state)


def recover():
    """Call at startup: re-queue interrupted jobs (bounded attempts) and resubmit queued ones."""
    db = session()
    try:
        for j in db.execute(select(Job).where(Job.state.in_(["RUNNING", "QUEUED"]))).scalars().all():
            if j.state == "RUNNING":
                if j.attempts >= MAX_ATTEMPTS:
                    j.state, j.error, j.finished_at = "FAILED", "interrupted too many times", now()
                    db.commit()
                    continue
                j.state = "QUEUED"
                db.commit()
                history.log(db, j.user_id, "job.recovered", "job", j.id, j.project_id, attempts=j.attempts)
            submit(j.id)
    finally:
        db.close()


def run_job(job_id):
    db = session()
    try:
        job = db.get(Job, job_id)
        if not job or job.state != "QUEUED":
            return
        if job.cancel_requested:
            job.state, job.finished_at, job.stop_reason, job.verification_status = "CANCELLED", now(), "cancelled", "unverified"
            db.commit()
            return
        job.state, job.started_at, job.attempts = "RUNNING", now(), job.attempts + 1
        db.execute(ValidationRound.__table__.delete().where(ValidationRound.job_id == job.id))  # clean restart of a recovered job
        db.commit()
        history.log(db, job.user_id, "job.running", "job", job.id, job.project_id, attempt=job.attempts)

        refs = []
        for rid in job.config.get("reference_ids", []):
            r = db.get(Reference, rid)
            if r and r.user_id == job.user_id:
                refs.append({"id": r.id, "name": r.name, "role": r.role, "text": r.text})
        task = job.prompt_text
        if refs:  # references are fenced as untrusted data
            task += "\n\n" + "\n\n".join(wrap_untrusted(r["name"], r["role"], r["text"]) for r in refs)

        def cancelled():
            db.refresh(job)
            return job.cancel_requested

        def stage(name):
            job.stage = name
            db.commit()

        def usage(snap):
            job.usage = snap
            db.commit()

        def on_round(rec):
            db.add(ValidationRound(job_id=job.id, index=rec["index"], output=rec["output"], stages=rec["stages"], issues=rec["issues"],
                                   repairs=rec["repairs"], compliance=rec["compliance"], cost=rec["cost"], seconds=rec["seconds"]))
            db.commit()
            history.log(db, job.user_id, "validation.round", "job", job.id, job.project_id, round=rec["index"],
                        issues=len(rec["issues"]), blocking=sum(1 for i in rec["issues"] if i["blocking"]), repairs=len(rec["repairs"]), cost=rec["cost"])

        try:
            eng = E.Engine(job.config, {"cancelled": cancelled, "stage": stage, "usage": usage, "round": on_round})
            res = eng.run(task, job.constraint_snapshot, refs)
        except Exception as e:  # noqa
            job.state, job.error, job.finished_at, job.verification_status = "FAILED", f"{type(e).__name__}: {e}", now(), "unverified"
            db.commit()
            history.log(db, job.user_id, "job.failed", "job", job.id, job.project_id, error=job.error)
            return
        job.usage = res["usage"]
        job.result = {"output": res["output"], "overridden_constraints": res["overridden_constraints"]}
        job.verification_status, job.stop_reason, job.stage, job.finished_at = res["verification_status"], res["stop_reason"], "", now()
        if res["stop_reason"] == "cancelled":
            job.state = "CANCELLED"
        elif res["stop_reason"] == "provider_error":
            job.state, job.error = "FAILED", res["error"]
        else:
            job.state = "COMPLETED"
        db.commit()
        history.log(db, job.user_id, "job.finished", "job", job.id, job.project_id, state=job.state, verification=job.verification_status,
                    stop_reason=job.stop_reason, cost=res["usage"]["cost"], calls=res["usage"]["calls"], seconds=res["usage"]["elapsed_seconds"])
    finally:
        db.close()


def wait_idle(timeout=30):
    """Test helper."""
    import time
    t = time.time()
    while time.time() - t < timeout:
        db = session()
        n = db.scalar(select(func.count()).select_from(Job).where(Job.state.in_(["QUEUED", "RUNNING"])))
        db.close()
        if not n:
            return True
        time.sleep(0.05)
    return False
