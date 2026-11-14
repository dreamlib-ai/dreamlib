"""Dreamlib API. Run from backend/: python -m app (or uvicorn app.main:app)."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import load_settings
from .errors import ApiError, code_for
from .routes import analysis, brain, dreams, jobs, events, journal, magazines, profile
from .services import Services, build_services
from .worker import Worker

log = logging.getLogger("dreamlib")

MAX_BODY = 1 << 20
MAX_AUDIO_BODY = analysis.MAX_AUDIO
API = "/api/v1"
LEGACY = "/api/"


class LegacyPaths:
    """Serves the old unversioned /api/... paths as /api/v1/... in place (no redirect, so bodies, audio
    uploads and streams pass untouched) and marks those answers deprecated. docs/api.md, S1."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith(LEGACY) or path.startswith(API + "/"):
            return await self.app(scope, receive, send)
        new = API + path[len(LEGACY) - 1:]
        scope = {**scope, "path": new, "raw_path": new.encode()}

        async def marked(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [(b"deprecation", b"true"), (b"link", f'<{new}>; rel="successor-version"'.encode())]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, marked)


def create_app(services: Services | None = None) -> FastAPI:
    """Builds the app. Tests pass their own services; otherwise they come from the environment."""
    s = services if services is not None else build_services(load_settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        """Runs the job worker beside the API unless workers is 0."""
        task = None
        if s.queue and s.workers > 0:
            s.worker = Worker(s, concurrency=s.workers)
            task = asyncio.create_task(s.worker.run())
        try:
            yield
        finally:
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            s.worker = None

    app = FastAPI(title="Dreamlib", version="1", docs_url="/docs", redoc_url=None, lifespan=lifespan,
                  generate_unique_id_function=lambda route: route.name)  # operation ids = function names (S3)
    app.state.services = s

    @app.exception_handler(ApiError)
    async def api_error(_: Request, e: ApiError):
        return JSONResponse({"error": e.message, "code": e.code}, status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def bad_request(_: Request, __: RequestValidationError):
        return JSONResponse({"error": "geçersiz istek", "code": "invalid_request"}, status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, e: StarletteHTTPException):
        message = "geçersiz istek" if e.status_code == 400 else "bulunamadı" if e.status_code == 404 else str(e.detail)
        return JSONResponse({"error": message, "code": code_for(e.status_code)}, status_code=e.status_code)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("unexpected error", exc_info=e)
        return JSONResponse({"error": "beklenmeyen hata", "code": "internal"}, status_code=500)

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        limit = MAX_AUDIO_BODY if request.url.path == f"{API}/transcribe" else MAX_BODY
        if int(request.headers.get("content-length") or 0) > limit:
            return JSONResponse({"error": "istek çok büyük", "code": "too_large"}, status_code=413)
        return await call_next(request)

    @app.get("/healthz")
    async def health(request: Request):
        s = request.app.state.services
        queued = None
        if s.queue:
            try:
                queued = await s.queue.depth()
            except Exception:
                log.warning("health: queue depth failed", exc_info=True)
        return {
            "ok": True, "llm": bool(s.llm), "images": bool(s.images), "accounts": bool(s.store), "speech": bool(s.speech),
            "editor": bool(s.editor), "worker": bool(s.worker), "queued": queued,
        }

    for module in (analysis, jobs, dreams, events, journal, profile, brain, magazines):
        app.include_router(module.router, prefix=API)
    app.add_middleware(LegacyPaths)  # outermost: the body limit and the router already see /api/v1
    return app


def app_factory() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # the worker looks at the queue every few seconds
    return create_app()
