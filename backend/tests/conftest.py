import json
import time

import pytest
from fastapi.testclient import TestClient

from app.providers.fal import Fal
from app.providers.openrouter import TASKS
from app.store.devstore import DevStore
from app.store.jobstore import MemoryJobs
from app.main import create_app
from app.services import Services

TOKEN = "dev-testuser-one"
OTHER = "dev-testuser-two"

ANALYSIS = {
    "title": "Uçan orman", "cleanText": "Ormanın üstünde uçuyordum.", "tags": ["uçmak", "orman"], "mood": "huzurlu",
    "interpretation": "Özgürlük arzusu.", "objects": [{"label": "orman", "meaning": "bilinçaltı"}],
    "emotions": [{"label": "huzur", "pct": 100.0, "note": "sakin"}],
}


class FakeLLM:
    """Remembers the system prompt and answers with a fixed reply (or reply(system, user))."""

    def __init__(self, reply):
        self.reply, self.system = reply, ""

    async def chat(self, messages, json_mode=False, *, task):
        assert task in TASKS, task  # every call site names a known task
        self.system, self.task = messages[0]["content"], task
        return self.reply(messages) if callable(self.reply) else self.reply


class FakeFal:
    """Queues instantly; calls holds ("generate", prompt, n) or ("edit", prompt, image_urls) per submit."""

    image_body, edit_body = staticmethod(Fal.image_body), staticmethod(Fal.edit_body)
    price = 0.01

    def __init__(self, text="Dün gece uçuyordum."):
        self.text, self.calls, self.fail = text, [], False

    async def submit(self, body):
        edit = "image_urls" in body
        self.calls.append(("edit", body["prompt"], body["image_urls"]) if edit else ("generate", body["prompt"], body["num_images"]))
        if self.fail:
            raise RuntimeError("fal down")
        prefix = "e" if edit else ""
        return {"urls": [f"https://fal.example/{prefix}{len(self.calls)}-{i}.png" for i in range(body["num_images"])]}

    async def images(self, handle):
        return handle["urls"]

    async def transcribe(self, audio, content_type, language=""):
        self.calls.append(("transcribe", len(audio), content_type, language))
        return self.text


def storyboard(n):
    return json.dumps({"characterNote": "a girl in a red coat", "panels": [{"caption": f"Sahne {i}", "scene": f"scene {i}"} for i in range(n)]})


def make_client(**overrides):
    dev = DevStore()
    s = Services(
        llm=FakeLLM(json.dumps(ANALYSIS)), images=FakeFal(), editor=FakeFal(), speech=FakeFal(), auth=dev, store=dev,
        queue=MemoryJobs(), workers=2,
    )
    for k, v in overrides.items():
        setattr(s, k, v)
    return TestClient(create_app(s)), s


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr("app.worker.BACKOFF", (0, 0, 0))  # retries after a transient error at once
    client, s = make_client()
    with client:
        yield client, s


def auth(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def wait_job(client, job_id, headers=None, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}", headers=headers or auth()).json()
        if job["status"] not in ("queued", "running"):
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")
