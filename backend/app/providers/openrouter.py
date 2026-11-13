"""A minimal chat-completions client for https://openrouter.ai."""
import asyncio
import logging
import time

import httpx

log = logging.getLogger("dreamlib")

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
RETRY_AFTER = 2  # one more try on a rate limit or a server error


class OpenRouter:
    def __init__(self, key: str, model: str):
        self.key, self.model = key, model
        self.http = httpx.AsyncClient(timeout=90)

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.model)

    async def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        payload: dict = {"model": self.model, "messages": messages, "usage": {"include": True}}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        for attempt in range(2):
            res = await self.http.post(ENDPOINT, json=payload, headers={"Authorization": f"Bearer {self.key}", "X-Title": "Dreamlib"})
            if attempt == 0 and (res.status_code == 429 or res.status_code >= 500):
                await asyncio.sleep(RETRY_AFTER)
                continue
            break
        if res.status_code // 100 != 2:
            raise RuntimeError(f"openrouter: status {res.status_code}: {res.text[:300]}")
        body = res.json()
        usage = body.get("usage") or {}
        log.info("openrouter: %s %.1fs %s tokens $%s", self.model, time.monotonic() - started, usage.get("total_tokens", "?"), usage.get("cost", "?"))
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("openrouter: empty choices")
        return choices[0]["message"]["content"]
