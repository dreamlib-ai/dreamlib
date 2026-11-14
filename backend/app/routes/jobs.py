"""Background work over HTTP: queue a manga booklet or pictures, follow a job, redraw a panel.
The work itself is done by the worker (app/worker.py); these routes only read and write the queue."""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..classification import Perspective

from ..errors import ApiError
from ..models import MangaMeta, Panel
from ..pipelines import image
from ..pipelines.manga import PANEL_COUNTS, REDO_TIMEOUT, panels_of, refresh_reference, render
from ..prompts import STYLE_HINTS
from ..services import Services, current_user, remove_files, services, sign_panels
from ..store.jobstore import Busy, Job
from .analysis import dream_text

log = logging.getLogger("dreamlib")
router = APIRouter()


class MangaIn(BaseModel):
    title: str = ""
    text: str = ""
    style: str = ""
    panels: int = 0
    consistent: bool = True  # same character in every panel; on unless switched off
    requestId: UUID | None = None
    useAvatar: bool = False
    avatarRevision: int = Field(default=0,ge=0)
    perspective: Perspective = 'unknown'


class ImagesIn(BaseModel):
    prompt: str = ""
    style: str = ""
    count: int = 1


async def _queue(s: Services, user_id: str, kind: str, input: dict, total: int, request_id: str = "") -> dict:
    async def existing():
        job = await s.queue.get(request_id, user_id) if request_id else None
        if job:
            if job.kind != kind or job.input != input or job.total != total:
                raise ApiError(409, "bu işlem başka bir çizime ait")
            return {"id": job.id}
        return None

    if found := await existing():
        return found
    limit = s.daily_guest if s.auth.is_guest(user_id) else s.daily_user
    if limit:
        try:
            used = await s.queue.count_since(user_id, datetime.now(timezone.utc) - timedelta(days=1))
        except Exception:
            log.exception("jobs: quota check failed")
            raise ApiError(502, "iş başlatılamadı")
        if used >= limit:
            raise ApiError(429, f"bugünlük {limit} çizim hakkın doldu, yarın yine gel")
    try:
        job = await s.queue.create(user_id, kind, input, total, request_id)
    except Busy:
        if found := await existing():
            return found
        raise ApiError(429, "önceki işin hâlâ hazırlanıyor")
    except Exception:
        log.exception("jobs: create failed")
        raise ApiError(502, "iş başlatılamadı")
    s.wake()
    return {"id": job.id}


@router.post("/manga", status_code=202)
async def start_manga(body: MangaIn, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """Validates the request and queues the booklet; the answer is the job id to follow."""
    if not s.llm or not s.images:
        raise ApiError(503, "görsel servisi kurulu değil")
    try:
        text = dream_text(body.text)
    except ApiError:
        raise ApiError(400, "rüya metni geçersiz")
    style = body.style or "manga"
    if style not in STYLE_HINTS:
        raise ApiError(400, "bilinmeyen stil")
    n = body.panels or 4
    if n not in PANEL_COUNTS:
        raise ApiError(400, "panel sayısı 4, 6 ya da 9 olmalı")
    if body.consistent and not s.editor:
        raise ApiError(503, "karakter tutarlılığı servisi kurulu değil")
    input = {"title": body.title, "text": text, "style": style, "consistent": body.consistent}
    if body.requestId:
        old = await s.queue.get(str(body.requestId),user_id)
        if old:
            same = old.kind == 'manga' and old.total == n and all(old.input.get(key) == value for key,value in input.items())
            same = same and old.input.get('perspective','unknown') == body.perspective and bool(old.input.get('avatarPath')) == body.useAvatar
            same = same and (not body.useAvatar or old.input.get('avatarRevision') == body.avatarRevision)
            if not same:
                raise ApiError(409,'bu işlem başka bir çizime ait')
            return {'id':old.id}
    if body.perspective != 'unknown':
        input['perspective'] = body.perspective
    if body.useAvatar:
        if not body.consistent:
            raise ApiError(400,'avatarla çizimde tutarlılık açık olmalı')
        profile = await s.store.get_profile(user_id)
        if profile.revision != body.avatarRevision:
            raise ApiError(409,'avatarın değişti; çizimi yeniden başlatabilirsin')
        if not profile.avatar or not profile.avatarPath:
            raise ApiError(400,'önce bir avatar seç')
        input.update(avatarPath=profile.avatarPath,avatarSpec=profile.avatar.model_dump(),avatarRevision=profile.revision)
    return await _queue(s, user_id, "manga", input, n, str(body.requestId) if body.requestId else "")


@router.post("/images", status_code=202)
async def start_images(body: ImagesIn, user_id: str = Depends(current_user), s: Services = Depends(services)):
    if not s.images:
        raise ApiError(503, "görsel servisi kurulu değil")
    prompt = body.prompt.strip()
    if not prompt:
        raise ApiError(400, "görsel tarifi boş")
    if len(prompt) > image.MAX_PROMPT:
        raise ApiError(400, "görsel tarifi çok uzun")
    style = body.style or "manga"
    if style not in STYLE_HINTS:
        raise ApiError(400, "bilinmeyen stil")
    return await _queue(s, user_id, "image", {"prompt": prompt, "style": style}, min(max(body.count, 1), image.MAX_IMAGES))


def job_panels(job: Job) -> list[Panel]:
    """One entry per picture the job makes; empty until it is drawn."""
    made = panels_of(job.state) if job.kind == "manga" else [Panel(path=p) for p in job.state.get("paths", [])]
    return made + [Panel() for _ in range(job.total - len(made))]


async def job_or_404(s: Services, job_id: str, user_id: str) -> Job:
    try:
        job = await s.queue.get(job_id, user_id)
    except Exception:
        log.exception("jobs: get failed")
        raise ApiError(502, "iş okunamadı")
    if not job:
        raise ApiError(404, "iş bulunamadı")
    return job


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user_id: str = Depends(current_user), s: Services = Depends(services)):
    j = await job_or_404(s, job_id, user_id)
    panels = job_panels(j)
    if j.status == "done":
        await sign_panels(s, [panels])
    status = "running" if j.status == "queued" else j.status  # the web app knows running, done and failed
    out = {"id": j.id, "status": status, "done": j.done, "total": j.total, "panels": [p.public() for p in panels], "error": j.error}
    if status in ("queued", "running") and j.state.get("eta_at"):
        out["etaSeconds"] = max(0, round(j.state["eta_at"] - time.time()))  # learned estimate, see app/eta.py
    return out


@router.post("/jobs/{job_id}/panels/{n}/redo")
async def redo_panel(job_id: str, n: int, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """Draws panel n of a finished booklet again and swaps it in."""
    async with s.locks.hold(user_id, None):
        j = await job_or_404(s, job_id, user_id)
        if j.kind != "manga" or not 0 <= n < j.total:
            raise ApiError(400, "panel numarası geçersiz")
        if j.status != "done":
            raise ApiError(409, "kitapçık henüz hazır değil")
        if not s.images:
            raise ApiError(503, "görsel servisi kurulu değil")
        await s.take("redo", user_id)
        meta, panels = MangaMeta.model_validate(j.state["meta"]), panels_of(j.state)
        try:
            async with asyncio.timeout(REDO_TIMEOUT):
                try:
                    await refresh_reference(s, meta, panels)
                except Exception:
                    log.exception("manga: reference failed")
                    raise ApiError(502, "karakter referansı açılamadı")
                try:
                    path, _ = await render(s, user_id, meta, n)
                except Exception:
                    log.exception("manga: redo failed (panel %d)", n)
                    raise ApiError(502, "panel yeniden çizilemedi")
        except TimeoutError:
            raise ApiError(502, "panel yeniden çizilemedi")
        old, j.state["paths"][n] = j.state["paths"][n], path
        if not await s.queue.update(j.id, {"state": j.state}):
            raise ApiError(502, "yeni panel kaydedilemedi")
    if not j.state.get("saved"):  # a saved dream still shows the old picture
        await remove_files(s, [old])
    panel = Panel(caption=panels[n].caption, path=path)
    await sign_panels(s, [[panel]])
    return panel.public()
