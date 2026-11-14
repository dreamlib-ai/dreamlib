"""Saved-dream types shared by the routes and the stores. Field names match the JSON the web app uses."""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from .classification import ClassificationOverride, Features
from .avatar import AvatarSpec


def _round(v):
    return round(v) if isinstance(v, float) else v


class DreamObject(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)  # answers always carry every field
    label: str = ""
    meaning: str = ""


class Emotion(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)  # answers always carry every field
    label: str = ""
    pct: Annotated[int, BeforeValidator(_round)] = 0
    note: str = ""


class Analysis(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)  # answers always carry every field
    title: str = ""
    cleanText: str = ""
    tags: list[str] = []
    mood: str = ""
    interpretation: str = ""
    objects: list[DreamObject] = []
    emotions: list[Emotion] = []
    features: Features = Field(default_factory=Features)


class CleanOut(BaseModel):
    """What the clean task returns."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)  # answers always carry every field
    cleanText: str = ""
    language: str = ""


class StoryPanel(BaseModel):
    scene: str
    caption: str = ""


class Storyboard(BaseModel):
    """What the storyboard task returns."""
    characterNote: str = ""
    panels: list[StoryPanel] = []


class Panel(BaseModel):
    """One picture of a booklet. path is a storage path (or, without storage, the remote image
    URL); url is the viewable address, filled in when a dream is sent out."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True,
                              json_schema_extra=lambda s, _=None: s.__setitem__("required", [r for r in s.get("required", []) if r in ("caption", "path")]))

    caption: str = ""
    path: str = ""
    url: str = ""
    # G3, filled in when sent out from the images table; never stored with the dream
    width: int = 0
    height: int = 0
    blurhash: str = ""
    color: str = ""
    thumb: str = ""  # viewable address of the 480 px copy

    def stored(self) -> dict:
        return {"caption": self.caption, "path": self.path}

    def public(self) -> dict:
        out = {**self.stored(), **({"url": self.url} if self.url else {})}
        if self.width:
            out.update(width=self.width, height=self.height, blurhash=self.blurhash, color=self.color)
        if self.thumb:
            out["thumb"] = self.thumb
        return out


class MangaMeta(BaseModel):
    """The storyboard, kept so saved panels can be redrawn after a restart. The aliases are the
    keys already stored in the database."""

    model_config = ConfigDict(populate_by_name=True)

    style: str = Field("", alias="Style")
    character_note: str = Field("", alias="CharacterNote")
    scenes: Annotated[list[str], BeforeValidator(lambda v: v or [])] = Field([], alias="Scenes")
    ref_url: str = Field("", alias="RefURL")
    consistent: bool = Field(False, alias="Consistent")
    avatar_path: str = Field('',alias='AvatarPath')
    avatar_spec: AvatarSpec | None = Field(None,alias='AvatarSpec')
    perspective: str = Field('unknown',alias='Perspective')
    prompt_version: str = Field('', alias='PromptVersion')  # picture prompt revision; empty is the legacy wording
    image_model: str = Field('', alias='ImageModel')  # registry name the panels were first drawn with


class DreamIn(Analysis):
    """What the client sends to save a dream. manga_meta is never taken from the client."""

    originalText: str = ""
    type: str = ""
    sleep: str = ""
    style: str = ""
    visibility: str = ""
    panels: list[Panel] = []
    jobId: str = ""
    analysisId: str = ""  # the analyses row /api/analyze returned; tied to the dream when it is saved


class JournalEntry(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)  # answers always carry every field
    id: str
    text: str = Field(min_length=1, max_length=4000)
    createdAt: datetime


class Journal(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)  # answers always carry every field
    dreamedOn: date | None = None
    favorite: bool = False
    reflection: str = Field(default="", max_length=4000)
    firstText: str = ""
    entries: list[JournalEntry] = Field(default_factory=list, max_length=50)
    analysisStale: bool = False
    artStale: bool = False
    classification: ClassificationOverride | None = None
    recall: str = Field(default='', pattern='^(|clear|fragmentary|faint)$')


class Dream(DreamIn):
    id: str = ""
    createdAt: datetime | None = None
    manga_meta: MangaMeta | None = None
    journal: Journal = Field(default_factory=Journal)
    revision: int = 0

    def public(self) -> dict:
        out = self.model_dump(mode="json", exclude={"manga_meta", "jobId", "panels", "analysisId"})
        out["panels"] = [p.public() for p in self.panels]
        return out
