import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.pipelines.registry import KINDS, UNKNOWN, UnknownKind, check
from app.store.jobstore import Job, MemoryJobs, SupabaseJobs
from app.worker import Worker


def run(coro):
    return asyncio.run(coro)


def test_registry_lists_the_running_kinds():
    assert set(KINDS) == {"manga", "image"}
    assert check("manga") is KINDS["manga"]
    with pytest.raises(UnknownKind):
        check("video")


def test_queues_refuse_an_unknown_kind_before_writing():
    q = MemoryJobs()
    with pytest.raises(UnknownKind):
        run(q.create("u1", "video", {}, 1))
    assert q.jobs == {}

    class NoNetwork:
        async def _do(self, *a, **kw):
            raise AssertionError("must not reach Supabase")

    with pytest.raises(UnknownKind):
        run(SupabaseJobs(NoNetwork()).create("u1", "video", {}, 1))


def test_worker_fails_a_job_of_a_kind_it_does_not_know():
    async def go():
        q = MemoryJobs()
        q.jobs["j1"] = Job(id="j1", user_id="u1", kind="video", created_at=datetime.now(timezone.utc))  # queued by another build
        w = Worker(SimpleNamespace(queue=q, blobs=None))
        job = await q.claim(w.name, 60, 3)
        await w.run_one(job)
        done = await q.get("j1", "u1")
        assert done.status == "failed" and done.error == UNKNOWN
        assert not await q.active("u1")  # the user can start a new job

    run(go())
