"""Small, content-free pilot funnel in structured service logs; no dream payloads."""
import hashlib
import json
import logging
import time
from collections import deque
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from ..errors import ApiError
from ..services import current_user

router = APIRouter()
log = logging.getLogger("dreamlib.events")
EventName = Literal["session_open", "record_started", "transcript_ready", "analysis_ready", "booklet_ready", "dream_saved", "feedback_helpful", "feedback_unhelpful"]

class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: EventName
    eventId: UUID
    platform: Literal["ios", "android", "desktop", "other"] = "other"

@router.post("/api/events", status_code=204)
async def event(body: EventIn, user_id: str = Depends(current_user)):
    now = time.monotonic()
    actor = hashlib.sha256(("dreamlib-events:" + user_id).encode()).hexdigest()[:20]
    # Bounded, per-process throttling. Logs can be deduplicated by name/actor/eventId.
    while recent and recent[0][0] < now - 60:
        recent.popleft()
    if sum(1 for _, who in recent if who == actor) >= 60:
        raise ApiError(429, "biraz bekleyip tekrar dene")
    recent.append((now, actor))
    if len(recent) > 5000:
        recent.popleft()
    log.info("product_event %s", json.dumps({"name": body.name, "actor": actor,
        "eventId": str(body.eventId), "platform": body.platform}, separators=(",", ":")))

recent: deque[tuple[float, str]] = deque()
