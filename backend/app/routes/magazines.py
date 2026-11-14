"""G4: a dream's magazine, laid out by the `magazine` job from its saved panels; the reader (G5) draws it."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends

from ..contract import MagazineOut, answers
from ..errors import ApiError
from ..models import Panel
from ..pipelines.magazine import MagazineSpec
from ..services import Services, current_user, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()


@router.get("/dreams/{dream_id}/magazine", **answers(MagazineOut, 200))
async def magazine(dream_id: str, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """404 until the job has laid it out (follow it on /dreams/{id}/status) and for dreams without pictures."""
    if not s.magazines:
        raise ApiError(503, "dergi servisi kurulu değil")
    try:
        row = await s.magazines.for_dream(user_id, dream_id)
    except Exception:
        log.exception("magazine: read failed")
        raise ApiError(502, "dergi açılamadı")
    if not row:
        raise ApiError(404, "bu rüyanın dergisi yok")
    spec = MagazineSpec.model_validate(row["spec"])
    panels = [Panel(caption=p.caption, path=p.path) for p in spec.panels]
    await sign_panels(s, [panels])
    updated = row["updated_at"]
    return {"id": row["id"], "dreamId": row["dream_id"], "status": row["status"], "visibility": row["visibility"],
            "spec": spec.model_dump(mode="json", exclude={"panels"}), "panels": [p.public() for p in panels],
            "updatedAt": updated if isinstance(updated, str) else datetime.isoformat(updated)}
