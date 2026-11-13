"""The services the routes use, and the helpers that look at them. Every one may be None: that
feature then answers 503 or falls back."""
import json
import logging
import time
import unicodedata
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import Request

from .config import Settings
from .errors import ApiError
from .models import Panel
from .providers.fake import FakeFal, FakeLLM
from .providers.fal import Fal
from .providers.openrouter import OpenRouter
from .store.devstore import DevStore
from .store.jobstore import MemoryJobs, SupabaseJobs
from .store.quota import SupabaseQuota
from .store.supabase import Supabase, Unauthorized

log = logging.getLogger("dreamlib")

MAX_DREAM = 4000


DAY = 86400
LOCK_FOR = 4 * 60  # longer than a panel redraw; a crashed process's lock frees itself after this


class UserLocks:
    """One panel or save operation per user at a time, and none while a job of theirs is going.
    Held in Postgres (store.quota) when accounts are on, so every API process sees the same lock;
    in memory for dev and tests."""

    def __init__(self, store=None):
        self.store = store
        self.busy: set[str] = set()

    @asynccontextmanager
    async def hold(self, user_id: str, queue):
        if self.store:
            token = await self.store.lock(user_id, LOCK_FOR, no_jobs=queue is not None)
            if not token:
                raise ApiError(409, "panel işlemi sürüyor")
            try:
                yield
            finally:
                try:
                    await self.store.unlock(user_id, token)
                except Exception:
                    log.warning("lock: release failed, it expires on its own", exc_info=True)
            return
        if user_id in self.busy or (queue and await queue.active(user_id)):
            raise ApiError(409, "panel işlemi sürüyor")
        self.busy.add(user_id)
        try:
            yield
        finally:
            self.busy.discard(user_id)


class CallLimits:
    """Paid calls each user may make in a rolling day, per kind ("text", "redo"), with a smaller
    allowance for guests. Counted in Postgres (store.quota) when accounts are on; in memory for dev
    and tests, where a restart forgives. Booklets and pictures are counted in the jobs table instead."""

    MESSAGES = {"text": "bugünlük {n} yorum hakkın doldu, yarın yine gel", "redo": "bugünlük {n} panel yenileme hakkın doldu"}

    def __init__(self, limits: dict[str, tuple[int, int]] | None = None, store=None):
        self.limits = limits or {}  # kind -> (guest, user); 0 or missing is no limit
        self.store = store
        self.calls: dict[tuple[str, str], deque[float]] = {}

    async def take(self, kind: str, user_id: str, guest: bool) -> None:
        """Counts one call, or answers 429 when the day's allowance is used up."""
        n = self.limits.get(kind, (0, 0))[0 if guest else 1]
        if not n:
            return
        ok = await self.store.take(user_id, kind, n, DAY) if self.store else self._take_here(kind, user_id, n)
        if not ok:
            raise ApiError(429, self.MESSAGES[kind].format(n=n))

    def _take_here(self, kind: str, user_id: str, n: int) -> bool:
        now = time.monotonic()
        q = self.calls.setdefault((kind, user_id), deque())
        while q and now - q[0] > DAY:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        return True

    async def sweep(self) -> None:
        if self.store:
            await self.store.sweep(DAY)


@dataclass
class Services:
    llm: OpenRouter | None = None  # None when OpenRouter is not configured
    images: Fal | None = None  # None when fal is not configured
    editor: Fal | None = None  # None: later panels cannot keep the same character
    speech: Fal | None = None  # None when speech to text is off
    auth: object | None = None  # needs user_id(token); None when accounts are not configured
    store: object | None = None  # dreams of each user; None when accounts are not configured
    blobs: Supabase | None = None  # None in dev: panels keep their remote URLs
    queue: object | None = None  # background jobs (SupabaseJobs or MemoryJobs); comes with accounts
    workers: int = 2  # jobs this process runs at a time; 0 leaves them to `python -m app.worker`
    daily_guest: int = 0  # jobs a guest may start in 24 hours; 0 is no limit
    daily_user: int = 0
    worker: object | None = None  # the running Worker, set when the app starts
    locks: UserLocks = field(default_factory=UserLocks)
    limits: CallLimits = field(default_factory=CallLimits)

    async def take(self, kind: str, user_id: str) -> None:
        await self.limits.take(kind, user_id, bool(self.auth and self.auth.is_guest(user_id)))

    def wake(self) -> None:
        if self.worker:
            self.worker.wake()


def build_services(cfg: Settings) -> Services:
    def on(client):
        return client if client.enabled else None

    sb = Supabase(cfg.supabase_url, cfg.supabase_service_key)
    s = Services(
        llm=on(OpenRouter(cfg.openrouter_key, cfg.openrouter_model)),
        images=on(Fal(cfg.fal_key, cfg.fal_image_model)),
        editor=on(Fal(cfg.fal_key, cfg.fal_edit_model)),
        speech=on(Fal(cfg.fal_key, cfg.fal_speech_model)),
        workers=cfg.workers,
        daily_guest=cfg.daily_guest,
        daily_user=cfg.daily_user,
        limits=CallLimits({"text": (cfg.daily_text_guest, cfg.daily_text_user), "redo": (cfg.daily_redo_guest, cfg.daily_redo_user)}),
    )
    if sb.enabled:
        s.auth, s.store, s.blobs, s.queue = sb, sb, sb, SupabaseJobs(sb)
        quota = SupabaseQuota(sb)
        s.limits.store, s.locks = quota, UserLocks(quota)
    elif cfg.dev_auth:
        s.auth = s.store = DevStore()
        s.queue = MemoryJobs()
        log.warning("DREAMLIB_DEV_AUTH=1: in-memory accounts, any 'dev-' token is accepted. Local use only.")
    else:
        log.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY missing: saving dreams is off")
    if cfg.fake_ai:
        if sb.enabled:
            raise SystemExit("DREAMLIB_FAKE_AI=1 is for local work; turn it off when Supabase is configured")
        s.llm, s.images, s.editor, s.speech = FakeLLM(), FakeFal("image"), FakeFal("edit"), FakeFal("speech")
        log.warning("DREAMLIB_FAKE_AI=1: stand-in model and picture answers. Local use only.")
    if not s.llm:
        log.warning("OPENROUTER_API_KEY or OPENROUTER_MODEL missing: /api/analyze is off")
    if not s.images:
        log.warning("FAL_KEY missing: pictures and /api/transcribe are off")
    return s


def services(request: Request) -> Services:
    return request.app.state.services


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else ""


async def current_user(request: Request) -> str:
    """Dependency for routes that need a signed-in user: 503 when accounts are off, 401 without a valid token."""
    s = services(request)
    if not s.auth or not s.store:
        raise ApiError(503, "hesap servisi kurulu değil")
    token = _bearer(request)
    if not token:
        raise ApiError(401, "giriş gerekli")
    try:
        return await s.auth.user_id(token)
    except Unauthorized:
        raise ApiError(401, "oturum geçersiz")
    except Exception:
        log.exception("auth failed")
        raise ApiError(401, "oturum geçersiz")


def extract_json(text: str) -> dict:
    """Parse the outermost JSON object of a model reply (code fences and chatter around it are fine)."""
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1] if 0 <= start <= end else text)


def one_line(text: str, limit: int) -> str:
    """Keeps free text from changing a prompt's shape: no line breaks, a length cap."""
    text = "".join(" " if unicodedata.category(c) == "Cc" else c for c in text)
    return " ".join(text.split())[:limit]


def clip(text: str, limit: int) -> str:
    return text[:limit]


async def sign_panels(s: Services, groups: list[list[Panel]]) -> None:
    """Fills in the viewable URL of every panel (one storage call for the lot)."""
    todo: list[Panel] = []
    for g in groups:
        for p in g:
            if not s.blobs or p.path.startswith("https://"):
                p.url = p.path
            else:
                todo.append(p)
    if not todo:
        return
    try:
        urls = await s.blobs.sign([p.path for p in todo])
    except Exception:
        log.exception("storage: sign failed")
        return
    for p, u in zip(todo, urls):
        p.url = u



async def remove_files(s: Services, paths: list[str]) -> None:
    """Deletes stored pictures that nothing points to any more; remote URLs (dev) and errors are ignored."""
    paths = [p for p in paths if p and not p.startswith(("https://", "data:"))]
    if not paths or not s.blobs:
        return
    try:
        await s.blobs.remove(paths)
    except Exception:
        log.warning("storage: remove failed (%d files)", len(paths), exc_info=True)
