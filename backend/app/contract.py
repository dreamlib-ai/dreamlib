"""Response shapes of /api/v1 for the OpenAPI schema and the generated TypeScript client (S3).

Routes still build their answers as before; these models only document them (`answers()`), so adding
one never filters or reshapes a response. tests/test_contract.py checks real answers against them.
In the output schema every field is required unless `sometimes()` names it (sent only when set)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .avatar import AvatarSpec, PresetId
from .models import Analysis, Journal, Panel
from .pipelines.magazine import MagazineColophon, MagazineCover, MagazinePage

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
    model_config = ConfigDict(**OUT, json_schema_extra=sometimes("next"))
    dreams: list[DreamOut]
    next: str = ""  # only when more remain: the cursor for the next page (G7)


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


Relation = Literal["shares_content", "shares_concept", "shares_emotion", "near_in_time", "series"]  # series: drawn by the dreamer


class SharedNode(BaseModel):
    model_config = OUT
    kind: str
    key: str
    label: str


class BrainEvidence(BaseModel):
    model_config = ConfigDict(**OUT, json_schema_extra=sometimes("shared", "days"))
    shared: list[SharedNode] = []  # node relations: what the two dreams have in common, rarest first
    days: int = 0  # near_in_time: days apart


class BrainLink(BaseModel):
    model_config = OUT
    relation: Relation
    source: str
    target: str
    weight: float
    evidence: BrainEvidence


class BrainDream(BaseModel):
    model_config = OUT
    id: str
    title: str
    dated: str  # YYYY-MM-DD: the day it was dreamt, else the day it was saved
    emotions: list[str]  # Hall–Van de Castle classes stated in the narrative (anger, apprehension, …)
    thumbnail: str  # the first panel's viewable address, empty without pictures
    degree: int  # links kept; 0 floats free in the graph


class BrainEdit(BaseModel):
    """BG4: the dreamer links two dreams (link) or hides a scored link between them (hide); on=false undoes it."""
    a: str
    b: str
    action: Literal["link", "hide"]
    on: bool = True


class BrainOut(BaseModel):
    model_config = OUT
    relations: list[Relation]  # legend order
    dreams: list[BrainDream]
    links: list[BrainLink]


class MagazineSpecOut(BaseModel):
    """What the reader draws; page and cover panels are indexes into the answer's `panels`."""
    model_config = OUT
    version: int
    cover: MagazineCover
    pages: list[MagazinePage]
    colophon: MagazineColophon


class MagazineOut(BaseModel):
    model_config = OUT
    id: str
    dreamId: str
    status: Literal["ready", "withdrawn"]
    visibility: Literal["private", "link", "public"]
    spec: MagazineSpecOut
    panels: list[Panel]  # signed, with G3 layout facts
    updatedAt: datetime


def answers(model: type[BaseModel] | None, status: int = 200) -> dict:
    """Route kwargs that document `model` as the answer without making FastAPI validate or filter it."""
    if model is None:
        return {"responses": {status: {"description": "Boş yanıt"}}}
    return {"response_model": None, "responses": {status: {"model": model, "description": "Başarılı"}}}

