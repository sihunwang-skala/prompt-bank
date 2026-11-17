import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator

SECTION_KEYS = ["body", "objective", "context", "instructions", "constraints", "output_format", "references", "evaluation_criteria"]


class Creds(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(min_length=8, max_length=200)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class PromptIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    sections: dict[str, str] = {}
    tags: list[str] = []
    folder: str = ""
    favorite: bool = False

    @field_validator("sections")
    @classmethod
    def _s(cls, v):
        bad = set(v) - set(SECTION_KEYS)
        if bad:
            raise ValueError(f"unknown sections: {sorted(bad)}")
        return v


class PromptPatch(BaseModel):
    title: str | None = None
    sections: dict[str, str] | None = None
    tags: list[str] | None = None
    folder: str | None = None
    favorite: bool | None = None
    change_note: str = ""


class BuildIn(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    model: str = "mock-1"


class ConstraintIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    scope: Literal["global", "project", "task_package", "execution"] = "project"
    priority: int = Field(50, ge=0, le=100)
    severity: Literal["critical", "major", "minor"] = "major"
    check: dict = {"type": "semantic"}
    project_id: str | None = None
    source: str = "user"


class ConstraintPatch(BaseModel):
    content: str | None = None
    priority: int | None = Field(None, ge=0, le=100)
    severity: Literal["critical", "major", "minor"] | None = None
    check: dict | None = None
    status: Literal["active", "disabled"] | None = None
    reason: str = ""


class ResolveIn(BaseModel):
    action: Literal["replace_existing", "keep_existing", "keep_both_priority"]


class ValidationCfg(BaseModel):
    max_iterations: int = Field(3, ge=1, le=10)
    max_cost: float | None = Field(0.5, ge=0)
    max_seconds: float = Field(120, ge=5, le=3600)
    review_depth: Literal["quick", "standard", "deep"] = "standard"
    model: str = "mock-1"
    reviewer_model: str | None = None
    reference_ids: list[str] = []


class RunIn(BaseModel):
    project_id: str
    prompt_id: str | None = None
    segment_ids: list[str] | None = None
    task: str | None = None
    config: ValidationCfg = ValidationCfg()
    constraint_ids: list[str] | None = None
    extra_constraints: list[ConstraintIn] = []


class MidChange(BaseModel):
    mode: Literal["apply_next", "cancel_restart", "branch"]
    constraint: ConstraintIn


class FormField(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,40}$")
    label: str = Field(max_length=120)
    type: Literal["text", "textarea", "number", "select", "boolean", "url", "file"]
    required: bool = False
    options: list[str] = []

    @field_validator("label")
    @classmethod
    def _no_markup(cls, v):
        if re.search(r"[<>]", v):
            raise ValueError("markup not allowed")
        return v


class FormSchema(BaseModel):
    """Declarative only: a closed set of field types. Never code."""
    fields: list[FormField] = Field(max_length=30)


class PackageIn(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=200)
    prompt_id: str
    reference_ids: list[str] = []
    form_schema: FormSchema = FormSchema(fields=[])
    model_settings: ValidationCfg = ValidationCfg()
    constraint_ids: list[str] = []
    evaluation_criteria: str = ""
    form_values: dict = {}


class RefUrl(BaseModel):
    project_id: str
    url: str
    role: str = "background"


class ReportIn(BaseModel):
    project_id: str
    request: str = ""
    type: str | None = None
    lang: Literal["en", "ko"] = "en"


class SettingsIn(BaseModel):
    allow_external_providers: bool | None = None
    default_model: str | None = None
    default_max_cost: float | None = None
    retention_days: int | None = Field(None, ge=1, le=3650)
    lang: Literal["en", "ko"] | None = None


class ExtractIn(BaseModel):
    segment_ids: list[str] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)


class StrengthenIn(BaseModel):
    addition: str = Field(min_length=1, max_length=4000)
    note: str = ""


class ComposePart(BaseModel):
    prompt_id: str
    segment_ids: list[str] = Field(min_length=1)


class ComposeIn(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    parts: list[ComposePart] = Field(min_length=1, max_length=30)
