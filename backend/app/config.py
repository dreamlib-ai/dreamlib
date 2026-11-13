"""Settings from the environment, plus an optional backend/.env file."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from .providers.openrouter import TASKS, Routes


def load_dotenv(path: Path) -> None:
    """Set KEY=VALUE lines from path without overriding real environment variables."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("\"'")
        if not os.environ.get(key):
            os.environ[key] = val


@dataclass(frozen=True)
class Settings:
    addr: str = "127.0.0.1:8080"
    openrouter_key: str = ""
    openrouter_model: str = ""
    openrouter_routes: Routes = field(default_factory=dict)  # per task: OPENROUTER_MODEL_<TASK>, OPENROUTER_FALLBACK_<TASK>
    fal_key: str = ""
    fal_image_model: str = "fast"  # a name in providers/image_models.toml, or a full fal id
    fal_edit_model: str = "consistent"  # draws later panels from the first one
    fal_speech_model: str = "speech"  # speech to text
    supabase_url: str = ""
    supabase_service_key: str = ""  # server-side only: bypasses row-level security
    supabase_public_url: str = ""  # browsers' address of the project when it differs (local Docker); else supabase_url
    dev_auth: bool = False  # in-memory accounts for local work, never in production
    fake_ai: bool = False  # stand-in LLM and fal answers for local work without keys, never in production
    workers: int = 2  # jobs the API process runs at a time; 0 when `python -m app.worker` runs them
    daily_guest: int = 3  # booklets and pictures a guest may start in 24 hours; 0 is no limit
    daily_user: int = 10  # the same for a signed-up user
    daily_text_guest: int = 30  # clean, analyze and transcribe calls a guest may make in 24 hours
    daily_text_user: int = 100
    daily_redo_guest: int = 10  # panel redraws
    daily_redo_user: int = 30


def llm_routes(env) -> Routes:
    """Per-task models from the environment; tasks with nothing set are left out."""
    routes: Routes = {}
    for task in TASKS:
        model = (env(f"OPENROUTER_MODEL_{task.upper()}") or "").strip()
        fallbacks = tuple(m.strip() for m in (env(f"OPENROUTER_FALLBACK_{task.upper()}") or "").split(",") if m.strip())
        if model or fallbacks:
            routes[task] = (model, fallbacks)
    return routes


def load_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    env = os.environ.get
    return Settings(
        addr=env("ADDR") or Settings.addr,
        openrouter_key=env("OPENROUTER_API_KEY", ""),
        openrouter_model=env("OPENROUTER_MODEL", ""),
        openrouter_routes=llm_routes(env),
        fal_key=env("FAL_KEY", ""),
        fal_image_model=env("FAL_IMAGE_MODEL") or Settings.fal_image_model,
        fal_edit_model=env("FAL_EDIT_MODEL") or Settings.fal_edit_model,
        fal_speech_model=env("FAL_SPEECH_MODEL") or Settings.fal_speech_model,
        supabase_url=env("SUPABASE_URL", ""),
        supabase_service_key=env("SUPABASE_SERVICE_KEY", ""),
        supabase_public_url=env("SUPABASE_PUBLIC_URL", ""),
        dev_auth=env("DREAMLIB_DEV_AUTH") == "1",
        fake_ai=env("DREAMLIB_FAKE_AI") == "1",
        workers=int(env("DREAMLIB_WORKERS") or Settings.workers),
        daily_guest=int(env("DAILY_LIMIT_GUEST") or Settings.daily_guest),
        daily_user=int(env("DAILY_LIMIT_USER") or Settings.daily_user),
        daily_text_guest=int(env("DAILY_TEXT_GUEST") or Settings.daily_text_guest),
        daily_text_user=int(env("DAILY_TEXT_USER") or Settings.daily_text_user),
        daily_redo_guest=int(env("DAILY_REDO_GUEST") or Settings.daily_redo_guest),
        daily_redo_user=int(env("DAILY_REDO_USER") or Settings.daily_redo_user),
    )
