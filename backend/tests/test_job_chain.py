import asyncio
import json

import httpx
import pytest

from app.pipelines.registry import KINDS, Kind
from app.store.jobstore import Busy, Duplicate, MemoryJobs, SupabaseJobs
from app.store.supabase import Supabase

UID = "0a1b2c3d-0000-4000-8000-000000000001"
DREAM = "0a1b2c3d-0000-4000-8000-0000000000dd"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def background(monkeypatch):
    """A free-running background kind, like index or glyph will be."""
    async def noop(ctx):
        return None

    monkeypatch.setitem(KINDS, "index", Kind(noop, 30, "x", exclusive=False, priority=0))


def test_only_exclusive_kinds_hold_the_one_active_job_rule(background):
    async def go():
        q = MemoryJobs()
        draw = await q.create("u1", "manga", {}, 4)
        a = await q.create("u1", "index", {}, 1, dream_id=DREAM)
        b = await q.create("u1", "index", {}, 1, parent_id=a.id)  # background work is never Busy
        with pytest.raises(Busy):
            await q.create("u1", "image", {}, 1)
        assert (draw.exclusive, a.exclusive) == (True, False)
        assert a.dream_id == DREAM and b.parent_id == a.id

    run(go())


def test_dedupe_key_returns_the_existing_job(background):
    async def go():
        q = MemoryJobs()
        first = await q.create("u1", "index", {}, 1, dedupe_key=f"index:{DREAM}")
        with pytest.raises(Duplicate) as dup:
            await q.create("u1", "index", {}, 1, dedupe_key=f"index:{DREAM}")
        assert dup.value.job.id == first.id
        await q.create("u2", "index", {}, 1, dedupe_key=f"index:{DREAM}")  # another user's is their own

    run(go())


def test_waited_on_jobs_are_claimed_before_background_work(background):
    async def go():
        q = MemoryJobs()
        bg = await q.create("u1", "index", {}, 1)
        drawn = await q.create("u2", "image", {}, 1)
        assert (await q.claim("w", 60, 3)).id == drawn.id
        assert (await q.claim("w", 60, 3)).id == bg.id

    run(go())


def test_supabase_create_sends_the_kind_rules_and_resolves_duplicates(background):
    row = {"id": "0a1b2c3d-0000-4000-8000-0000000000bb", "user_id": UID, "kind": "index", "status": "done", "dedupe_key": "k"}
    seen = []

    def handler(req: httpx.Request):
        if req.method == "POST":
            seen.append(json.loads(req.content))
            return httpx.Response(409, json={"code": "23505"})
        return httpx.Response(200, json=[row])

    q = SupabaseJobs(Supabase("https://x.supabase.co", "service-key", transport=httpx.MockTransport(handler)))
    with pytest.raises(Duplicate) as dup:
        run(q.create(UID, "index", {}, 1, dream_id=DREAM, dedupe_key="k"))
    assert dup.value.job.id == row["id"]
    assert seen[0] | {"input": {}} == {"user_id": UID, "kind": "index", "input": {}, "total": 1, "priority": 0,
                                         "exclusive": False, "dream_id": DREAM, "dedupe_key": "k"}
    with pytest.raises(Busy):  # without a key, a 409 is the one-active-job rule
        run(q.create(UID, "manga", {}, 4))
