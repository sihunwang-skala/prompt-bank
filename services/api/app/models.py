from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, now, new_id


def _pk(prefix):
    return mapped_column(String(40), primary_key=True, default=lambda: new_id(prefix))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = _pk("usr")
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = _pk("prj")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[str] = _pk("prm")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    folder: Mapped[str] = mapped_column(String(120), default="")
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[str] = _pk("pv")
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    sections: Mapped[dict] = mapped_column(JSON)  # objective/context/instructions/constraints/output_format/references/evaluation_criteria
    change_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Constraint(Base):
    """Current head of a constraint. Every change also writes a ConstraintVersion row."""
    __tablename__ = "constraints"
    id: Mapped[str] = _pk("con")  # constraint_id
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    package_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default="user")
    scope: Mapped[str] = mapped_column(String(20), default="project")  # global|project|task_package|execution
    priority: Mapped[int] = mapped_column(Integer, default=50)  # 0..100, higher wins
    severity: Mapped[str] = mapped_column(String(20), default="major")  # critical|major|minor
    status: Mapped[str] = mapped_column(String(24), default="active")  # active|superseded|disabled|conflicting|pending_approval
    version: Mapped[int] = mapped_column(Integer, default=1)
    verification_method: Mapped[str] = mapped_column(String(24), default="semantic")  # deterministic|semantic
    check: Mapped[dict] = mapped_column("check_spec", JSON, default=dict)  # {"type": ..., params}
    conflicts_with: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ConstraintVersion(Base):
    __tablename__ = "constraint_versions"
    id: Mapped[str] = _pk("cv")
    constraint_id: Mapped[str] = mapped_column(ForeignKey("constraints.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Reference(Base):
    __tablename__ = "references"
    id: Mapped[str] = _pk("ref")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(10))  # file|url
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    mime: Mapped[str] = mapped_column(String(100), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(24), default="background")
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")  # extracted text (untrusted data)
    extraction: Mapped[str] = mapped_column(String(24), default="ok")  # ok|unsupported|empty
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TaskPackage(Base):
    __tablename__ = "task_packages"
    id: Mapped[str] = _pk("pkg")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class TaskPackageVersion(Base):
    __tablename__ = "task_package_versions"
    id: Mapped[str] = _pk("pkv")
    package_id: Mapped[str] = mapped_column(ForeignKey("task_packages.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = _pk("job")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    prompt_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    package_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    parent_job_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    state: Mapped[str] = mapped_column(String(24), default="QUEUED", index=True)
    stage: Mapped[str] = mapped_column(String(60), default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # frozen at creation
    constraint_snapshot: Mapped[list] = mapped_column(JSON, default=list)  # frozen at start
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_status: Mapped[str] = mapped_column(String(24), default="")
    stop_reason: Mapped[str] = mapped_column(String(40), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    estimate: Mapped[dict] = mapped_column(JSON, default=dict)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)  # tokens, cost, calls, retries
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ValidationRound(Base):
    __tablename__ = "validation_rounds"
    id: Mapped[str] = _pk("rnd")
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    output: Mapped[str] = mapped_column(Text, default="")
    stages: Mapped[dict] = mapped_column(JSON, default=dict)  # stage name -> structured result
    issues: Mapped[list] = mapped_column(JSON, default=list)
    repairs: Mapped[list] = mapped_column(JSON, default=list)
    compliance: Mapped[list] = mapped_column(JSON, default=list)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HistoryEvent(Base):
    __tablename__ = "history_events"
    id: Mapped[str] = _pk("evt")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
