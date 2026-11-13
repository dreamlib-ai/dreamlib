"""A minimal chat-completions and embeddings client for https://openrouter.ai.

Every call names a task. The task picks the model list (OPENROUTER_MODEL_<TASK>, then
OPENROUTER_FALLBACK_<TASK>, else OPENROUTER_MODEL) and the timeout; code never names a model."""
import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from .errors import ProviderError

log = logging.getLogger("dreamlib")

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
EMBED_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
EMBED_BATCH = 64  # texts per embeddings request
RETRY_AFTER = 2  # one more try on a rate limit or a server error

# Seconds a task may take. See docs/llm.md for what each task is.
TASKS: dict[str, float] = {
    "clean": 30,
    "extract": 60,
    "interpret": 120,
    "storyboard": 120,
    "embed": 30,
    "moderate": 20,
}

Routes = dict[str, tuple[str, tuple[str, ...]]]  # task -> (model, fallbacks)


@dataclass(frozen=True)
class Embeddings:
    """Vectors in the order of the texts, and the model that made them: vectors of different models
    live in different spaces, so the model is stored next to every vector (docs/motor.md)."""

    model: str
    vectors: list[list[float]]

    @property
    def dims(self) -> int:
        return len(self.vectors[0]) if self.vectors else 0


class OpenRouter:
    def __init__(self, key: str, model: str, routes: Routes | None = None):
        self.key, self.model, self.routes = key, model, routes or {}
        self.meter = None  # app.usage.Meter, set by build_services
        self.http = httpx.AsyncClient()

    @property
    def enabled(self) -> bool:
        return bool(self.key and (self.model or any(m for m, _ in self.routes.values())))

    def models_for(self, task: str) -> list[str]:
        """The task's model, its fallbacks, in order and without repeats; the default model if none is set."""
        if task not in TASKS:
            raise ValueError(f"openrouter: unknown task {task!r}")
        model, fallbacks = self.routes.get(task, ("", ()))
        return [m for m in dict.fromkeys((model or self.model, *fallbacks)) if m]

    async def _post(self, url: str, payload: dict, task: str) -> httpx.Response:
        for attempt in range(2):
            res = await self.http.post(
                url, json=payload, timeout=TASKS[task],
                headers={"Authorization": f"Bearer {self.key}", "X-Title": "Dreamlib"},
            )
            if attempt == 0 and (res.status_code == 429 or res.status_code >= 500):
                await asyncio.sleep(RETRY_AFTER)
                continue
            break
        if res.status_code // 100 != 2:
            raise ProviderError(f"openrouter: {task} status {res.status_code}: {res.text[:300]}", res.status_code)
        return res

    async def chat(self, messages: list[dict], json_mode: bool = False, *, task: str) -> str:
        models = self.models_for(task)
        if not models:
            raise RuntimeError(f"openrouter: no model for task {task}")
        payload: dict = {"messages": messages, "usage": {"include": True}}
        if len(models) > 1:
            payload["models"] = models  # OpenRouter tries them in order
        else:
            payload["model"] = models[0]
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        body = (await self._post(ENDPOINT, payload, task)).json()
        usage = body.get("usage") or {}
        log.info("openrouter: %s %s %.1fs %s tokens $%s", task, body.get("model", models[0]), time.monotonic() - started,
                 usage.get("total_tokens", "?"), usage.get("cost", "?"))
        if self.meter:
            await self.meter.record("openrouter", body.get("model", models[0]), task,
                                    usage.get("total_tokens") or 0, "tokens", float(usage.get("cost") or 0))
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("openrouter: empty choices")
        return choices[0]["message"]["content"]

    async def embed(self, texts: list[str]) -> Embeddings:
        """Vectors for texts with the `embed` task's model. Its fallbacks are not tried: a vector from
        another model cannot be compared with the stored ones, so a failure is an error, not a switch."""
        if not texts:
            return Embeddings("", [])
        models = self.models_for("embed")
        if not models:
            raise RuntimeError("openrouter: no model for task embed")
        model, vectors, used, tokens = models[0], [], "", 0
        started = time.monotonic()
        for i in range(0, len(texts), EMBED_BATCH):
            batch = texts[i:i + EMBED_BATCH]
            payload = {"model": model, "input": batch, "encoding_format": "float"}
            body = (await self._post(EMBED_ENDPOINT, payload, "embed")).json()
            rows = sorted(body.get("data") or [], key=lambda r: r.get("index", 0))
            if len(rows) != len(batch):
                raise RuntimeError(f"openrouter: embed returned {len(rows)} vectors for {len(batch)} texts")
            for r in rows:
                vec = r.get("embedding")
                if not isinstance(vec, list) or not vec or not all(isinstance(x, (int, float)) for x in vec):
                    raise RuntimeError("openrouter: embed returned a malformed vector")
                vectors.append([float(x) for x in vec])
            used = used or body.get("model") or model
            tokens += (body.get("usage") or {}).get("total_tokens") or 0
        if len({len(v) for v in vectors}) != 1:
            raise RuntimeError("openrouter: embed returned vectors of different sizes")
        log.info("openrouter: embed %s %.1fs %d texts %d dims %s tokens", used, time.monotonic() - started,
                 len(texts), len(vectors[0]), tokens or "?")
        return Embeddings(used, vectors)
