"""fal.ai: image generation and editing through the queue API (https://queue.fal.run), speech to
text through the synchronous endpoint. One client per model.

A queued request is a handle of two URLs. Pipelines keep the handle in the job's state, so after a
restart the worker asks fal for the same picture instead of paying for a new one.

Models come from image_models.toml (price, typical time). fal gives no time estimate, so every
request this process queued is timed and fed to app.eta, which predicts the next ones."""
import asyncio
import logging
import time

import httpx

from .. import eta
from .errors import ProviderError
from .image_models import FalModel

log = logging.getLogger("dreamlib")

QUEUE = "https://queue.fal.run"
POLL_EVERY = 1.0
WAIT_FOR = 180


class Fal:
    def __init__(self, key: str, spec: FalModel):
        self.key, self.spec = key, spec
        self.model, self.task = spec.id, spec.role  # task: image, edit or speech, for usage rows
        self.eta = None  # app.eta.Estimator, set by build_services
        self._timing: dict[str, tuple[float, list[float]]] = {}  # status_url -> (queued at, features)
        self.meter = None  # app.usage.Meter, set by build_services
        self.http = httpx.AsyncClient(timeout=60)

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.model)

    @property
    def price(self) -> float:
        return self.spec.price

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
            raise ProviderError(f"fal: submit status {res.status_code}: {res.text[:300]}", res.status_code)
        d = res.json()
        if not d.get("status_url") or not d.get("response_url"):
            raise RuntimeError("fal: bad queue reply")
        if self.meter:  # counted when queued: a restart reads the same request again without paying
            n = body.get("num_images", 1)
            await self.meter.record("fal", self.model, self.task, n, "images", self.price * n)
        x = eta.features(body.get("num_images", 1), len(body.get("image_urls", [])))
        self._timing[d["status_url"]] = (eta.clock(), x)  # only requests queued here are timed
        return {"status_url": d["status_url"], "response_url": d["response_url"]}

    async def estimate(self, pictures: int = 1, references: int = 0, queue_position: int = 0) -> float:
        """Seconds from queueing to the picture, as learned so far; the typical time before any data."""
        x = eta.features(pictures, references, queue_position)
        if not self.eta:
            return self.spec.typical_seconds * max(1, pictures)
        return await self.eta.estimate(self.model, self.spec.typical_seconds, x)

    async def images(self, handle: dict, wait_for: float = WAIT_FOR) -> list[str]:
        """Waits for a queued request and returns its picture URLs."""
        deadline = time.monotonic() + wait_for
        timing, first = self._timing.pop(handle["status_url"], None), True
        while True:
            st = await self.http.get(handle["status_url"], headers=self._auth)
            if st.status_code // 100 != 2:
                raise ProviderError(f"fal: status {st.status_code}: {st.text[:300]}", st.status_code)
            body = st.json()
            if first and timing:  # the queue position when we first looked is a feature too
                timing[1][3] = float(body.get("queue_position") or 0)
            first = False
            if body.get("status") == "COMPLETED":
                if timing and self.eta:
                    inference = (body.get("metrics") or {}).get("inference_time")
                    await self.eta.observe(self.model, self.spec.typical_seconds, timing[1], eta.clock() - timing[0], inference)
                break
            if time.monotonic() > deadline:
                raise ProviderError("fal: request timed out", 0)
            await asyncio.sleep(POLL_EVERY)
        res = await self.http.get(handle["response_url"], headers=self._auth)
        if res.status_code // 100 != 2:
            raise ProviderError(f"fal: result status {res.status_code}: {res.text[:300]}", res.status_code)
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
            raise ProviderError(f"fal: status {res.status_code}: {res.text[:300]}", res.status_code)
        if self.meter:
            await self.meter.record("fal", self.model, self.task, 1, "requests", 0.0)
        return res.json().get("text", "").strip()

    async def _upload(self, data: bytes, content_type: str) -> str:
        res = await self.http.post(
            "https://rest.alpha.fal.ai/storage/upload/initiate",
            json={"file_name": "audio", "content_type": content_type},
            headers=self._auth,
        )
        if res.status_code // 100 != 2:
            raise ProviderError(f"fal: upload init status {res.status_code}", res.status_code)
        slot = res.json()
        if not slot.get("upload_url") or not slot.get("file_url"):
            raise RuntimeError("fal: bad upload slot")
        put = await self.http.put(slot["upload_url"], content=data, headers={"Content-Type": content_type})
        if put.status_code // 100 != 2:
            raise ProviderError(f"fal: upload status {put.status_code}", put.status_code)
        return slot["file_url"]
