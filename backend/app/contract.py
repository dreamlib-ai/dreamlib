"""Response shapes of /api/v1 for the OpenAPI schema and the generated TypeScript client (S3).

Routes still build their answers as before; these models only document them (`answers()`), so adding
one never filters or reshapes a response. tests/test_contract.py checks real answers against them.
In the output schema every field is required unless `sometimes()` names it (sent only when set)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .avatar import AvatarSpec, PresetId
from .models import Analysis, Journal, Panel

OUT = ConfigDict(json_schema_serialization_defaults_required=True)
JobStatus = Literal["running", "done", "failed"]


def sometimes(*names: str):
    """json_schema_extra that leaves these fields out of `required`: the answer omits them when empty."""

    def extra(schema: dict[str, Any], _cls=None) -> None:
        schema["required"] = [r for r in schema.get("required", []) if r not in names]
        if not schema["required"]:
            schema.pop("required")

    return extra


class AnalysisOut(Analysis):
    model_config = ConfigDict(**OUT, json_schema_extra=sometimes("analysisId"))
    analysisId: str = ""  # only when the interpretation was recorded (M3)


class TranscribeOut(BaseModel):
    model_config = OUT
    text: str


class JobRef(BaseModel):
    model_config = OUT
    id: str


class JobOut(BaseModel):
    model_config = ConfigDict(**OUT, json_schema_extra=sometimes("etaSeconds"))
    id: str
    status: JobStatus
    done: int
    total: int
    panels: list[Panel]
    error: str
    etaSeconds: int = 0  # only while the job runs and an estimate exists


class DreamOut(Analysis):
    model_config = OUT
    id: str
    originalText: str
    type: str
    sleep: str
    style: str
    visibility: str
    panels: list[Panel]
    createdAt: datetime | None
    journal: Journal
    revision: int


class DreamList(BaseModel):
    model_config = OUT
    dreams: list[DreamOut]


class DreamJob(BaseModel):
    model_config = OUT
    id: str
    kind: str
    status: JobStatus
    done: int
    total: int
    error: str
    parentId: str | None


class DreamStatus(BaseModel):
    model_config = OUT
    dreamId: str
    busy: bool
    jobs: list[DreamJob]


class ProfileOut(BaseModel):
    model_config = OUT
    id: str
    displayName: str
    avatar: AvatarSpec | None
    presetId: PresetId | None
    revision: int
    avatarUrl: str


def answers(model: type[BaseModel] | None, status: int = 200) -> dict:
    """Route kwargs that document `model` as the answer without making FastAPI validate or filter it."""
    if model is None:
        return {"responses": {status: {"description": "Boş yanıt"}}}
    return {"response_model": None, "responses": {status: {"model": model, "description": "Başarılı"}}}

