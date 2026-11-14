"""G4: a dream's magazine, laid out by the `magazine` job from its saved panels; the reader (G5) draws it.
G6: its owner may open it to anyone with the link; /m/{slug} is then readable without signing in."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from ..contract import MagazineOut, MagazineShare, SharedMagazineOut, answers
from ..errors import ApiError
from ..models import Panel
from ..pipelines.magazine import MagazineSpec
from ..services import Services, current_user, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()
COVER_CACHE = 300  # seconds a link preview may keep the cover address; signed URLs live an hour


def _on(s: Services) -> None:
    if not s.magazines:
        raise ApiError(503, "dergi servisi kurulu değil")


async def _pages(s: Services, row: dict) -> tuple[dict, list[dict]]:
    spec = MagazineSpec.model_validate(row["spec"])
    panels = [Panel(caption=p.caption, path=p.path) for p in spec.panels]
    await sign_panels(s, [panels])
    return spec.model_dump(mode="json", exclude={"panels"}), [p.public() for p in panels]


async def _answer(s: Services, row: dict) -> dict:
    spec, panels = await _pages(s, row)
    updated = row["updated_at"]
    out = {"id": row["id"], "dreamId": row["dream_id"], "status": row["status"], "visibility": row["visibility"],
           "spec": spec, "panels": panels, "updatedAt": updated if isinstance(updated, str) else datetime.isoformat(updated)}
    if row["visibility"] != "private" and row.get("share_slug"):
        out["shareSlug"] = row["share_slug"]
    return out


@router.get("/dreams/{dream_id}/magazine", **answers(MagazineOut, 200))
async def magazine(dream_id: str, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """404 until the job has laid it out (follow it on /dreams/{id}/status) and for dreams without pictures."""
    _on(s)
    try:
        row = await s.magazines.for_dream(user_id, dream_id)
    except Exception:
        log.exception("magazine: read failed")
        raise ApiError(502, "dergi açılamadı")
    if not row:
        raise ApiError(404, "bu rüyanın dergisi yok")
    return await _answer(s, row)


@router.put("/dreams/{dream_id}/magazine/visibility", **answers(MagazineOut, 200))
async def share_magazine(dream_id: str, body: MagazineShare, user_id: str = Depends(current_user),
                         s: Services = Depends(services)):
    _on(s)
    try:
        row = await s.magazines.share(user_id, dream_id, body.visibility)
    except Exception:
        log.exception("magazine: share failed")
        raise ApiError(502, "paylaşım değiştirilemedi")
    if not row:
        raise ApiError(404, "bu rüyanın dergisi yok")
    return await _answer(s, row)


async def _shared(s: Services, slug: str) -> dict:
    _on(s)
    try:
        row = await s.magazines.by_slug(slug)
    except Exception:
        log.exception("magazine: shared read failed")
        raise ApiError(502, "dergi açılamadı")
    if not row:
        raise ApiError(404, "bu dergi paylaşılmıyor")
    return row


@router.get("/m/{slug}", **answers(SharedMagazineOut, 200))
async def shared_magazine(slug: str, s: Services = Depends(services)):
    """No sign-in: the shared magazine's pages, nothing about whose it is."""
    spec, panels = await _pages(s, await _shared(s, slug))
    return {"spec": spec, "panels": panels}


@router.get("/m/{slug}/cover", responses={302: {"description": "Kapak görseline yönlendirir"}})
async def shared_cover(slug: str, s: Services = Depends(services)):
    """A lasting address for link previews: sends on to a fresh signed copy of the cover (its thumbnail if any)."""
    row = await _shared(s, slug)
    spec = MagazineSpec.model_validate(row["spec"])
    cover = Panel(caption="", path=spec.panels[spec.cover.panel].path) if spec.panels else None
    if cover:
        await sign_panels(s, [[cover]])
    target = cover and (cover.thumb or cover.url)
    if not target:
        raise ApiError(404, "kapak görseli yok")
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": f"public, max-age={COVER_CACHE}"})
