"""The library: save, list, open, delete and redraw the dreams of the signed-in user."""
import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from .analysis import MAX_CONTEXT
from .jobs import job_or_404
from ..errors import ApiError, Conflict, NotFound
from ..pipelines.manga import REDO_TIMEOUT, panels_of, refresh_reference, render
from ..models import Dream, DreamIn, MangaMeta, Panel
from ..prompts import INTERPRETATION_HINTS, STYLE_HINTS
from ..providers.fake import PLACEHOLDER_PREFIX, FakeFal
from ..services import MAX_DREAM, Services, current_user, remove_files, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()

MAX_TITLE = 200
MAX_TAGS = 20
MAX_OBJECTS = 30
MAX_EMOTIONS = 12
MAX_URL = 2000
MAX_CAPTION = 300
MAX_PANELS = 9


def valid_path(s: Services, user_id: str, path: str) -> bool:
    """Only pictures this user could have made: their own storage folder, or (without storage, in dev) an https URL,
    or with DREAMLIB_FAKE_AI=1 the placeholder pictures the stand-in provider draws."""
    if not path or len(path) > MAX_URL:
        return False
    if not s.blobs:
        return path.startswith("https://") or (isinstance(s.images, FakeFal) and path.startswith(PLACEHOLDER_PREFIX))
    return path.startswith(user_id + "/") and ".." not in path


@router.post("/api/dreams", status_code=201)
async def save_dream(body: DreamIn, user_id: str = Depends(current_user), s: Services = Depends(services)):
    return await save_record(body, user_id, s)


@router.put("/api/dreams/{dream_id}")
async def put_dream(dream_id: UUID, body: DreamIn, existing: bool = False, user_id: str = Depends(current_user), s: Services = Depends(services)):
    return await save_record(body, user_id, s, str(dream_id), existing)


async def save_record(body: DreamIn, user_id: str, s: Services, dream_id: str = "", existing: bool = False):
    async with s.locks.hold(user_id, s.queue):
        d = Dream(**body.model_dump(), id=dream_id)
        previous = None
        if dream_id:
            try:
                previous = await s.store.get_dream(user_id, dream_id)
            except NotFound:
                pass
            if existing and previous is None:
                raise ApiError(404, "rüya silinmiş; yeni bir rüya başlatabilirsin")
            if previous and existing and previous.revision > 0 and d.originalText.strip() != previous.originalText:
                raise ApiError(409, "rüya kütüphanede değişti; güncel kaydı açıp devam et")
        if d.jobId:
            job = await job_or_404(s, d.jobId, user_id)
            if job.kind != "manga" or job.status != "done":
                raise ApiError(409, "kitapçık henüz hazır değil")
            if job.state.get("saved") and (not dream_id or job.state.get("savedDreamId") != dream_id):
                raise ApiError(409, "bu kitapçık zaten kaydedildi")
            meta = MangaMeta.model_validate(job.state["meta"])  # stored without a reference URL; redraws sign a fresh one
            d.panels, d.style, d.manga_meta = panels_of(job.state), meta.style, meta
        d.title, d.originalText = d.title.strip(), d.originalText.strip()

        if not d.originalText or len(d.originalText) > MAX_DREAM:
            raise ApiError(400, "rüya metni geçersiz")
        if not d.title or len(d.title) > MAX_TITLE:
            raise ApiError(400, "başlık geçersiz")
        if len(d.cleanText) > MAX_DREAM or len(d.interpretation) > 2 * MAX_DREAM:
            raise ApiError(400, "metin çok uzun")
        if len(d.mood) > MAX_CONTEXT or len(d.sleep) > MAX_CONTEXT:
            raise ApiError(400, "ruh hali ya da uyku bilgisi çok uzun")
        if len(d.tags) > MAX_TAGS or len(d.objects) > MAX_OBJECTS or len(d.emotions) > MAX_EMOTIONS:
            raise ApiError(400, "çok fazla öğe")
        d.type = d.type or "universal"
        if d.type not in INTERPRETATION_HINTS:
            raise ApiError(400, "bilinmeyen yorum türü")
        d.visibility = d.visibility or "private"  # dreams are private unless the user opens them up
        if d.visibility not in ("private", "public"):
            raise ApiError(400, "bilinmeyen görünürlük")
        d.style = d.style or "manga"
        if d.style not in STYLE_HINTS:
            raise ApiError(400, "bilinmeyen stil")
        if len(d.panels) > MAX_PANELS:
            raise ApiError(400, "çok fazla panel")
        for p in d.panels:
            if not valid_path(s, user_id, p.path) or len(p.caption) > MAX_CAPTION:
                raise ApiError(400, "panel geçersiz")
            p.caption, p.url = p.caption.strip(), ""  # the viewable URL is never stored

        # A text-only retry must not strip a booklet already attached to this record.
        if previous and not d.jobId:
            d.panels, d.manga_meta, d.style = previous.panels, previous.manga_meta, previous.style
        if previous:
            d.journal, d.revision = previous.journal, previous.revision + 1
            if d.jobId:
                d.journal.artStale = False
                # Keep journal state when a completed booklet is attached.
            if d.originalText != previous.originalText:
                d.journal.firstText = d.journal.firstText or previous.originalText
                d.journal.artStale = bool(d.panels) and not bool(d.jobId)
        try:
            saved = await s.store.save_dream(user_id, d)
        except NotFound:
            raise ApiError(404, "rüya bulunamadı")
        except Exception:
            log.exception("dreams: save failed")
            raise ApiError(502, "rüya kaydedilemedi")
        if d.jobId:  # the pictures belong to the dream now; the sweep must leave them alone
            try:
                await s.queue.update(job.id, {"state": {**job.state, "saved": True, "savedDreamId": saved.id}})
            except Exception:
                log.warning("dreams: could not mark job %s saved", job.id, exc_info=True)
        # Do not delete replaced image paths here: legacy records may share them.
    await sign_panels(s, [saved.panels])
    return saved.public()


@router.get("/api/dreams")
async def list_dreams(user_id: str = Depends(current_user), s: Services = Depends(services)):
    try:
        dreams = await s.store.list_dreams(user_id)
    except Exception:
        log.exception("dreams: list failed")
        raise ApiError(502, "kütüphane açılamadı")
    await sign_panels(s, [d.panels for d in dreams])
    return {"dreams": [d.public() for d in dreams]}


async def _load(s: Services, user_id: str, dream_id: str) -> Dream:
    try:
        return await s.store.get_dream(user_id, dream_id)
    except NotFound:
        raise ApiError(404, "rüya bulunamadı")
    except Exception:
        log.exception("dreams: get failed")
        raise ApiError(502, "rüya açılamadı")


@router.get("/api/dreams/{dream_id}")
async def get_dream(dream_id: str, user_id: str = Depends(current_user), s: Services = Depends(services)):
    d = await _load(s, user_id, dream_id)
    await sign_panels(s, [d.panels])
    return d.public()


@router.get("/api/dreams/{dream_id}/status")
async def dream_status(dream_id: str, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """Every job working for this dream (index, glyph, magazine...), so the app follows one address."""
    await _load(s, user_id, dream_id)  # 404 unless the dream is theirs
    if not s.queue:
        return {"dreamId": dream_id, "busy": False, "jobs": []}
    try:
        jobs = await s.queue.for_dream(user_id, dream_id)
    except Exception:
        log.exception("dreams: status failed")
        raise ApiError(502, "durum okunamadı")
    out = [{"id": j.id, "kind": j.kind, "status": "running" if j.status == "queued" else j.status,
            "done": j.done, "total": j.total, "error": j.error, "parentId": j.parent_id} for j in jobs]
    return {"dreamId": dream_id, "busy": any(j["status"] == "running" for j in out), "jobs": out}


@router.delete("/api/dreams/{dream_id}", status_code=204)
async def delete_dream(dream_id: str, user_id: str = Depends(current_user), s: Services = Depends(services)):
    files: list[str] = []
    if s.blobs:  # read the picture paths first: once the row is gone they are lost
        try:
            files = [p.path for p in (await s.store.get_dream(user_id, dream_id)).panels if not p.path.startswith("https://")]
        except Exception:
            pass
    try:
        await s.store.delete_dream(user_id, dream_id)
    except NotFound:
        raise ApiError(404, "rüya bulunamadı")
    except Exception:
        log.exception("dreams: delete failed")
        raise ApiError(502, "rüya silinemedi")
    if files:
        try:
            await s.blobs.remove(files)
        except Exception:
            log.exception("storage: remove failed (%d files)", len(files))  # the dream is gone; leftover files are only clutter
    return Response(status_code=204)


@router.post("/api/dreams/{dream_id}/panels/{n}/redo")
async def redo_saved_panel(dream_id: str, n: int, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """Works from the stored storyboard, independently of the job cache."""
    async with s.locks.hold(user_id, s.queue):
        d = await _load(s, user_id, dream_id)
        if not 0 <= n < len(d.panels):
            raise ApiError(400, "panel numarası geçersiz")
        if not d.manga_meta or len(d.manga_meta.scenes) != len(d.panels):
            raise ApiError(409, "bu kitapçığın çizim taslağı saklanmamış")
        if not s.images:
            raise ApiError(503, "görsel servisi kurulu değil")
        await s.take("redo", user_id)
        meta = d.manga_meta.model_copy(deep=True)
        try:
            async with asyncio.timeout(REDO_TIMEOUT):
                try:
                    await refresh_reference(s, meta, d.panels)
                except Exception:
                    log.exception("redo: reference failed")
                    raise ApiError(502, "karakter referansı açılamadı")
                try:
                    path, _ = await render(s, user_id, meta, n)
                except Exception:
                    log.exception("redo: render failed")
                    raise ApiError(502, "panel yeniden çizilemedi")
                after = [p.model_copy() for p in d.panels]
                after[n] = Panel(caption=d.panels[n].caption, path=path)
                meta.ref_url = ""  # never persist short-lived signed URLs
                try:
                    await s.store.replace_panels(user_id, d.id, d.panels, after, meta)
                except Exception as e:
                    # Only the newly generated, uncommitted file is safe to remove.
                    if s.blobs:
                        try:
                            await s.blobs.remove([path])
                        except Exception:
                            log.warning("redo cleanup failed", exc_info=True)
                    if isinstance(e, (Conflict, NotFound)):
                        raise ApiError(409, "rüya değişti, yeniden yükle")
                    log.exception("redo: save failed")
                    raise ApiError(502, "yeni panel kaydedilemedi")
        except TimeoutError:
            raise ApiError(502, "panel yeniden çizilemedi")
    await remove_files(s, [d.panels[n].path])  # the replaced picture is no longer part of the dream
    await sign_panels(s, [after])
    return after[n].public()
