import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.store.jobstore import Busy, MemoryJobs, SupabaseJobs
from app.store.supabase import Supabase

UID = "0a1b2c3d-0000-4000-8000-000000000001"
JID = "0a1b2c3d-0000-4000-8000-0000000000bb"
ROW = {"id": JID, "user_id": UID, "kind": "manga", "status": "queued", "input": {"text": "x"}, "total": 4}


def run(coro):
    return asyncio.run(coro)


def test_memory_queue_claims_in_order_and_fences_writes():
    async def go():
        q = MemoryJobs()
        a = await q.create("u1", "manga", {}, 4)
        with pytest.raises(Busy):
            await q.create("u1", "image", {}, 1)
        b = await q.create("u2", "image", {}, 1)

        first = await q.claim("w1", 60, 3)
        assert first.id == a.id and first.status == "running" and first.attempts == 1
        assert (await q.claim("w2", 60, 3)).id == b.id
        assert await q.claim("w3", 60, 3) is None

        assert await q.update(a.id, {"done": 1}, worker="w1", lease=60)
        assert not await q.update(a.id, {"done": 2}, worker="w2")  # not w2's job
        assert (await q.get(a.id, "u1")).done == 1 and await q.get(a.id, "u2") is None

        # w1 stalls: its lease runs out, another worker takes over and w1 can no longer write
        q.leases[a.id] = datetime.now(timezone.utc) - timedelta(seconds=1)
        again = await q.claim("w2", 60, 3)
        assert again.id == a.id and again.attempts == 2
        assert not await q.update(a.id, {"done": 3}, worker="w1")

        # out of attempts: the expired job fails for good
        q.jobs[a.id].attempts = 3
        q.leases[a.id] = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert await q.claim("w3", 60, 3) is None
        assert (await q.get(a.id, "u1")).status == "failed"
        day = datetime.now(timezone.utc) - timedelta(days=1)
        assert await q.count_since("u1", day) == 0 and await q.count_since("u2", day) == 1  # failed jobs are not counted

    run(go())


def test_supabase_queue_speaks_postgrest():
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        if req.url.path == "/rest/v1/rpc/claim_job":
            return httpx.Response(200, json=[{**ROW, "status": "running", "attempts": 1, "worker": "w1"}])
        if req.method == "POST":
            body = json.loads(req.content)
            return httpx.Response(409, json={"code": "23505"}) if body["user_id"] == "busy" else httpx.Response(201, json=[ROW])
        if req.method == "PATCH":
            return httpx.Response(200, json=[ROW] if req.url.params.get("worker") == "eq.w1" else [])
        return httpx.Response(200, json=[ROW])

    q = SupabaseJobs(Supabase("https://x.supabase.co", "service-key", transport=httpx.MockTransport(handler)))
    assert run(q.create(UID, "manga", {"text": "x"}, 4)).id == JID
    with pytest.raises(Busy):
        run(q.create("busy", "manga", {}, 4))

    job = run(q.claim("w1", 120, 3))
    assert job.worker == "w1" and json.loads(seen[-1].content) == {"p_worker": "w1", "p_lease_seconds": 120, "p_max_attempts": 3}

    assert run(q.update(JID, {"done": 1}, worker="w1", lease=120))
    patch = seen[-1]
    assert patch.url.params["status"] == "eq.running" and "lease_until" in json.loads(patch.content)
    assert not run(q.update(JID, {"done": 1}, worker="w2"))

    assert run(q.get("not-a-uuid", UID)) is None
    assert run(q.get(JID, UID)).kind == "manga"
    assert seen[-1].url.params["user_id"] == f"eq.{UID}"
