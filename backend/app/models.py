"""Saved-dream types shared by the routes and the stores. Field names match the JSON the web app uses."""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from .classification import ClassificationOverride, Features
from .avatar import AvatarSpec


def _round(v):
    return round(v) if isinstance(v, float) else v


class DreamObject(BaseModel):
    label: str = ""
    meaning: str = ""


class Emotion(BaseModel):
    label: str = ""
    pct: Annotated[int, BeforeValidator(_round)] = 0
    note: str = ""


class Analysis(BaseModel):
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

    caption: str = ""
    path: str = ""
    url: str = ""

    def stored(self) -> dict:
        return {"caption": self.caption, "path": self.path}

    def public(self) -> dict:
        return {**self.stored(), **({"url": self.url} if self.url else {})}


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


class JournalEntry(BaseModel):
    id: str
    text: str = Field(min_length=1, max_length=4000)
    createdAt: datetime


class Journal(BaseModel):
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
        out = self.model_dump(mode="json", exclude={"manga_meta", "jobId", "panels"})
        out["panels"] = [p.public() for p in self.panels]
        return out
