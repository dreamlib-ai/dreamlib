import asyncio
import json
from types import SimpleNamespace

import httpx

from app import worker
from app.pipelines.registry import KINDS, Kind
from app.providers.fal import Fal
from app.providers.image_models import resolve
from app.providers.openrouter import OpenRouter
from app.store.jobstore import MemoryJobs
from app.store.supabase import Supabase
from app.usage import MemoryUsage, Meter, SupabaseUsage, set_scope

UID = "0a1b2c3d-0000-4000-8000-000000000001"


def run(coro):
    return asyncio.run(coro)


def test_openrouter_writes_tokens_and_cost_for_the_user_in_scope():
    sink = MemoryUsage()
    llm = OpenRouter("key", "m/default")
    llm.meter = Meter(sink)
    llm.http = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={
        "model": "m/answered", "usage": {"total_tokens": 321, "cost": 0.0012}, "choices": [{"message": {"content": "ok"}}]})))

    async def go():
        set_scope(user_id=UID)
        await llm.chat([{"role": "user", "content": "x"}], task="clean")

    run(go())
    assert sink.rows == [{"provider": "openrouter", "model": "m/answered", "task": "clean", "units": 321, "unit": "tokens",
                          "cost_usd": 0.0012, "user_id": UID, "job_id": None}]


def test_fal_counts_pictures_when_queued_not_when_read_again():
    sink = MemoryUsage()
    fal = Fal("key", resolve("fast", "image"))
    fal.meter = Meter(sink)

    def handler(req: httpx.Request):
        if req.method == "POST":
            return httpx.Response(200, json={"status_url": "https://q/s", "response_url": "https://q/r"})
        if req.url.path == "/s":
            return httpx.Response(200, json={"status": "COMPLETED"})
        return httpx.Response(200, json={"images": [{"url": "https://img/1"}, {"url": "https://img/2"}]})

    fal.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def go():
        handle = await fal.submit(Fal.image_body("koala", 2))
        await fal.images(handle)
        await fal.images(handle)  # a restart reads the same request again

    run(go())
    assert len(sink.rows) == 1
    row = sink.rows[0]
    assert (row["provider"], row["task"], row["units"], row["unit"]) == ("fal", "image", 2, "images")
    assert abs(row["cost_usd"] - 0.006) < 1e-9


def test_a_failing_sink_never_breaks_the_call():
    class Down:
        async def insert(self, row):
            raise RuntimeError("db down")

    run(Meter(Down()).record("fal", "m", "image", 1, "images", 0.01))


def test_worker_rows_carry_the_job_and_its_owner(monkeypatch):
    sink = MemoryUsage()
    meter = Meter(sink)

    async def pipeline(ctx):
        await meter.record("fal", "m", "image", 1, "images", 0.01)

    monkeypatch.setitem(KINDS, "image", Kind(pipeline, 5, "x"))

    async def go():
        q = MemoryJobs()
        job = await q.create("u1", "image", {}, 1)
        w = worker.Worker(SimpleNamespace(queue=q, blobs=None))
        await w.run_one(await q.claim(w.name, 60, 3))
        return job.id

    job_id = run(go())
    assert (sink.rows[0]["user_id"], sink.rows[0]["job_id"]) == ("u1", job_id)


def test_supabase_rows_drop_ids_that_are_not_uuids():
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.url.path, json.loads(req.content)))
        return httpx.Response(201)

    sink = SupabaseUsage(Supabase("https://x.supabase.co", "service-key", transport=httpx.MockTransport(handler)))
    run(sink.insert({"provider": "fal", "model": "m", "task": "image", "units": 1, "unit": "images", "cost_usd": 0.01,
                     "user_id": UID, "job_id": "dev-hex-id"}))
    path, body = seen[0]
    assert path == "/rest/v1/usage" and body["user_id"] == UID and body["job_id"] is None
