"""fal.ai: image generation and editing through the queue API (https://queue.fal.run), speech to
text through the synchronous endpoint. One client per model.

A queued request is a handle of two URLs. Pipelines keep the handle in the job's state, so after a
restart the worker asks fal for the same picture instead of paying for a new one."""
import asyncio
import logging
import time

import httpx

log = logging.getLogger("dreamlib")

QUEUE = "https://queue.fal.run"
POLL_EVERY = 1.0
WAIT_FOR = 180

# Rough dollars per picture, for the cost estimate kept on each job (fal bills per megapixel).
PRICES = {"fal-ai/flux/schnell": 0.003, "fal-ai/flux/dev": 0.025, "fal-ai/nano-banana/edit": 0.039}


class Fal:
    def __init__(self, key: str, model: str):
        self.key, self.model = key, model
        self.http = httpx.AsyncClient(timeout=60)

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.model)

    @property
    def price(self) -> float:
        return PRICES.get(self.model, 0.0)

    @property
    def _auth(self) -> dict:
        return {"Authorization": f"Key {self.key}"}

    @staticmethod
    def image_body(prompt: str, n: int = 1) -> dict:
        return {"prompt": prompt, "num_images": n, "image_size": "square_hd"}

    @staticmethod
    def edit_body(prompt: str, image_urls: list[str], n: int = 1) -> dict:
        """Draw prompt using reference images (https URLs or data URIs); the model must take image_urls."""
        return {"prompt": prompt, "image_urls": image_urls, "num_images": n}

    async def submit(self, body: dict) -> dict:
        """Queues a request and returns its handle."""
        res = await self.http.post(f"{QUEUE}/{self.model}", json=body, headers=self._auth)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"fal: submit status {res.status_code}: {res.text[:300]}")
        d = res.json()
        if not d.get("status_url") or not d.get("response_url"):
            raise RuntimeError("fal: bad queue reply")
        return {"status_url": d["status_url"], "response_url": d["response_url"]}

    async def images(self, handle: dict, wait_for: float = WAIT_FOR) -> list[str]:
        """Waits for a queued request and returns its picture URLs."""
        deadline = time.monotonic() + wait_for
        while True:
            st = await self.http.get(handle["status_url"], headers=self._auth)
            if st.status_code // 100 != 2:
                raise RuntimeError(f"fal: status {st.status_code}: {st.text[:300]}")
            if st.json().get("status") == "COMPLETED":
                break
            if time.monotonic() > deadline:
                raise RuntimeError("fal: request timed out")
            await asyncio.sleep(POLL_EVERY)
        res = await self.http.get(handle["response_url"], headers=self._auth)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"fal: result status {res.status_code}: {res.text[:300]}")
        urls = [i["url"] for i in res.json().get("images", []) if i.get("url")]
        if not urls:
            raise RuntimeError("fal: no images returned")
        log.info("fal: %s %d picture(s) in %.1fs", self.model, len(urls), time.monotonic() - deadline + wait_for)
        return urls

    async def transcribe(self, audio: bytes, content_type: str, language: str = "") -> str:
        """fal does not take data URIs for audio, so the bytes go to fal's storage first."""
        body = {"audio_url": await self._upload(audio, content_type), "task": "transcribe", "chunk_level": "segment"}
        if language:
            body["language"] = language
        res = await self.http.post(f"https://fal.run/{self.model}", json=body, headers=self._auth, timeout=180)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"fal: status {res.status_code}: {res.text[:300]}")
        return res.json().get("text", "").strip()

    async def _upload(self, data: bytes, content_type: str) -> str:
        res = await self.http.post(
            "https://rest.alpha.fal.ai/storage/upload/initiate",
            json={"file_name": "audio", "content_type": content_type},
            headers=self._auth,
        )
        if res.status_code // 100 != 2:
            raise RuntimeError(f"fal: upload init status {res.status_code}")
        slot = res.json()
        if not slot.get("upload_url") or not slot.get("file_url"):
            raise RuntimeError("fal: bad upload slot")
        put = await self.http.put(slot["upload_url"], content=data, headers={"Content-Type": content_type})
        if put.status_code // 100 != 2:
            raise RuntimeError(f"fal: upload status {put.status_code}")
        return slot["file_url"]
