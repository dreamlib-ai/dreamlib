"""A minimal chat-completions client for https://openrouter.ai.

Every call names a task. The task picks the model list (OPENROUTER_MODEL_<TASK>, then
OPENROUTER_FALLBACK_<TASK>, else OPENROUTER_MODEL) and the timeout; code never names a model."""
import asyncio
import logging
import time

import httpx

from .errors import ProviderError

log = logging.getLogger("dreamlib")

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
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


class OpenRouter:
    def __init__(self, key: str, model: str, routes: Routes | None = None):
        self.key, self.model, self.routes = key, model, routes or {}
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
        for attempt in range(2):
            res = await self.http.post(
                ENDPOINT, json=payload, timeout=TASKS[task],
                headers={"Authorization": f"Bearer {self.key}", "X-Title": "Dreamlib"},
            )
            if attempt == 0 and (res.status_code == 429 or res.status_code >= 500):
                await asyncio.sleep(RETRY_AFTER)
                continue
            break
        if res.status_code // 100 != 2:
            raise ProviderError(f"openrouter: {task} status {res.status_code}: {res.text[:300]}", res.status_code)
        body = res.json()
        usage = body.get("usage") or {}
        log.info("openrouter: %s %s %.1fs %s tokens $%s", task, body.get("model", models[0]), time.monotonic() - started,
                 usage.get("total_tokens", "?"), usage.get("cost", "?"))
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("openrouter: empty choices")
        return choices[0]["message"]["content"]
