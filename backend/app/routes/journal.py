"""Owner-only edits with revision checks; original recollections remain available."""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from .analysis import AnalyzeIn, analyze
from .dreams import _load
from ..errors import ApiError, Conflict, NotFound
from ..models import Analysis, JournalEntry
from ..classification import ClassificationOverride
from ..services import Services, current_user, services, sign_panels

router = APIRouter()


class AdditionIn(BaseModel):
    id: UUID
    text: str = Field(min_length=1, max_length=4000)


class JournalPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    originalText: str | None = Field(default=None, min_length=1, max_length=4000)
    dreamedOn: date | None = None
    favorite: bool | None = None
    reflection: str | None = Field(default=None, max_length=4000)
    addition: AdditionIn | None = None
    refresh: bool = False
    personal: bool = False
    classification: ClassificationOverride | None = None
    recall: str | None = Field(default=None, pattern='^(|clear|fragmentary|faint)$')


@router.patch("/api/dreams/{dream_id}/journal")
async def edit_journal(dream_id: str, body: JournalPatch, user_id: str = Depends(current_user), s: Services = Depends(services)):
    async with s.locks.hold(user_id, s.queue):
        d = await _load(s, user_id, dream_id)
        if d.revision != body.revision:
            raise ApiError(409, "kayıt başka bir yerde değişti; yeniden açıp dene")
        if body.title is not None:
            if not body.title.strip():
                raise ApiError(400, "başlık boş olamaz")
            d.title = body.title.strip()
        if body.originalText is not None and body.originalText != d.originalText:
            if not body.originalText.strip():
                raise ApiError(400, "rüya boş olamaz")
            d.journal.firstText = d.journal.firstText or d.originalText
            d.originalText = body.originalText.strip()
            d.journal.analysisStale, d.journal.artStale = True, bool(d.panels)
        if "dreamedOn" in body.model_fields_set:
            # A calendar date can already be tomorrow in the user's local timezone.
            if body.dreamedOn and body.dreamedOn > datetime.now(timezone.utc).date() + timedelta(days=1):
                raise ApiError(400, "rüya tarihi gelecekte olamaz")
            d.journal.dreamedOn = body.dreamedOn
        if body.favorite is not None:
            d.journal.favorite = body.favorite
        if body.reflection is not None:
            d.journal.reflection = body.reflection.strip()
        if 'classification' in body.model_fields_set:
            d.journal.classification = body.classification
        if body.recall is not None:
            d.journal.recall = body.recall
        if body.addition:
            if not body.addition.text.strip():
                raise ApiError(400, "ayrıntı boş olamaz")
            if not any(e.id == str(body.addition.id) for e in d.journal.entries):
                if len(d.journal.entries) >= 50:
                    raise ApiError(400, "bu rüya için ayrıntı sınırına ulaştın")
                d.journal.entries.append(JournalEntry(id=str(body.addition.id), text=body.addition.text.strip(), createdAt=datetime.now(timezone.utc)))
                d.journal.analysisStale, d.journal.artStale = True, bool(d.panels)
        if body.refresh:
            # Thoughts stay outside the narrative. Never silently truncate recollections.
            narrative = d.originalText
            for entry in d.journal.entries:
                extra = "\nSonradan hatırladığım ayrıntı: " + entry.text
                if len(narrative) + len(extra) > 4000:
                    raise ApiError(400, "yorum için rüya ve ayrıntılarını 4000 karakterin altına indir")
                narrative += extra
            result = Analysis.model_validate(await analyze(AnalyzeIn(text=narrative, type=d.type, personal=body.personal, excludeId=UUID(d.id) if len(d.id) == 36 else None), user_id, s))
            for field in ("cleanText", "interpretation", "tags", "objects", "emotions", "features"):
                setattr(d, field, getattr(result, field))
            d.journal.analysisStale = False
        try:
            saved = await s.store.update_journal(user_id, d, body.revision)
        except Conflict:
            raise ApiError(409, "kayıt değişti; yeniden açıp dene")
        except NotFound:
            raise ApiError(404, "rüya bulunamadı")
    await sign_panels(s, [saved.panels])
    return saved.public()
