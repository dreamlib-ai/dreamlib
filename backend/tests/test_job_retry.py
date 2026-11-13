import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app import worker
from app.pipelines.registry import KINDS, Kind
from app.providers.errors import ProviderError, is_transient
from app.store.jobstore import MemoryJobs


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("exc,transient", [
    (ProviderError("x", 429), True),
    (ProviderError("x", 503), True),
    (ProviderError("x", 0), True),
    (ProviderError("x", 400), False),
    (ProviderError("x", 422), False),
    (httpx.ConnectError("down"), True),
    (TimeoutError(), True),
    (ValueError("unknown"), True),  # unknown errors get bounded retries
])
def test_error_classes(exc, transient):
    assert is_transient(exc) is transient


def test_class_follows_the_cause_chain():
    try:
        try:
            raise ProviderError("fal: status 400", 400)
        except ProviderError as e:
            raise RuntimeError("panel failed") from e
    except RuntimeError as wrapped:
        assert not is_transient(wrapped)


def test_backoff_grows_with_jitter_and_stops_growing():
    for attempt, base in [(1, 5), (2, 20), (3, 80), (9, 80)]:
        for _ in range(50):
            assert base * 0.75 <= worker.backoff(attempt) <= base * 1.25


def test_a_queued_job_waits_for_run_after():
    async def go():
        q = MemoryJobs()
        job = await q.create("u1", "image", {}, 1)
        q.jobs[job.id].run_after = datetime.now(timezone.utc) + timedelta(seconds=60)
        assert await q.claim("w", 60, 3) is None
        q.jobs[job.id].run_after = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert (await q.claim("w", 60, 3)).id == job.id

    run(go())


def fails_with(exc):
    async def pipeline(ctx):
        raise exc

    return Kind(pipeline, 5, "çizim başarısız")


def run_once(monkeypatch, exc):
    monkeypatch.setitem(KINDS, "image", fails_with(exc))

    async def go():
        q = MemoryJobs()
        job = await q.create("u1", "image", {}, 1)
        w = worker.Worker(SimpleNamespace(queue=q, blobs=None))
        await w.run_one(await q.claim(w.name, 60, 3))
        return q.jobs[job.id]

    return run(go())


def test_permanent_error_fails_on_the_first_try(monkeypatch):
    job = run_once(monkeypatch, ProviderError("fal: status 422", 422))
    assert job.status == "failed" and job.attempts == 1 and job.error == "çizim başarısız"


def test_transient_error_goes_back_to_the_queue_later(monkeypatch):
    before = datetime.now(timezone.utc)
    job = run_once(monkeypatch, ProviderError("fal: status 503", 503))
    assert job.status == "queued" and job.attempts == 1
    assert before + timedelta(seconds=3) <= job.run_after <= before + timedelta(seconds=8)
