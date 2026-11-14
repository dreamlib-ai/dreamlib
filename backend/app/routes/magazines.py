"""G4: a dream's magazine, laid out by the `magazine` job from its saved panels; the reader (G5) draws it.
G6: its owner may open it to anyone with the link; /m/{slug} is then readable without signing in."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse

from ..contract import MagazineOut, MagazineShare, SharedMagazineOut, answers
from ..errors import ApiError
from ..models import Panel
from ..pipelines.magazine import MagazineSpec
from ..services import Services, current_user, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()
PICTURE_CACHE = 3600  # seconds a shared picture may be kept; a redrawn panel shows within the hour


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
    """No sign-in: the shared magazine's pages, nothing about whose it is; pictures come from /m/{slug}/p/{n}."""
    spec = MagazineSpec.model_validate((await _shared(s, slug))["spec"])
    meta = {}
    if s.blobs and hasattr(s.blobs, "image_meta"):
        try:
            meta = await s.blobs.image_meta([p.path for p in spec.panels])
        except Exception:
            log.warning("magazine: shared picture facts unavailable", exc_info=True)
    panels = []
    for n, p in enumerate(spec.panels):
        out = {"caption": p.caption, "url": f"/api/v1/m/{slug}/p/{n}", "thumb": f"/api/v1/m/{slug}/p/{n}?thumb=true"}
        if m := meta.get(p.path):
            out.update(width=m["width"], height=m["height"], blurhash=m["blurhash"], color=m["color"])
        panels.append(out)
    return {"spec": spec.model_dump(mode="json", exclude={"panels"}), "panels": panels}


async def _picture(s: Services, slug: str, n: int | None, thumb: bool) -> Response:
    spec = MagazineSpec.model_validate((await _shared(s, slug))["spec"])
    n = spec.cover.panel if n is None else n
    if not 0 <= n < len(spec.panels):
        raise ApiError(404, "görsel yok")
    path = spec.panels[n].path
    if not s.blobs or path.startswith("https://"):
        return RedirectResponse(path, status_code=302)  # local work without storage: remote placeholder pictures
    if thumb and hasattr(s.blobs, "image_meta"):
        try:
            path = (await s.blobs.image_meta([path])).get(path, {}).get("thumb_path") or path
        except Exception:
            log.warning("magazine: thumbnail lookup failed", exc_info=True)
    try:
        data, kind = await s.blobs.read(path)
    except Exception:
        log.warning("magazine: shared picture unreadable", exc_info=True)
        raise ApiError(404, "görsel yok")
    return Response(data, media_type=kind, headers={"Cache-Control": f"public, max-age={PICTURE_CACHE}"})


@router.get("/m/{slug}/p/{n}", responses={200: {"description": "Görsel"}})
async def shared_picture(slug: str, n: int, thumb: bool = False, s: Services = Depends(services)):
    """A shared magazine's picture through our own address, so no storage path (which names the owner) leaves."""
    return await _picture(s, slug, n, thumb)


@router.get("/m/{slug}/cover", responses={200: {"description": "Kapak görseli"}})
async def shared_cover(slug: str, s: Services = Depends(services)):
    """A lasting address for link previews: the cover's thumbnail."""
    return await _picture(s, slug, None, True)
