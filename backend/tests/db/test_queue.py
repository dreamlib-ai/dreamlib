"""SupabaseJobs against the real jobs table, indexes and claim_job function."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import worker
from app.pipelines.registry import KINDS, Kind
from app.providers.errors import ProviderError
from app.store.jobstore import Busy, Duplicate, SupabaseJobs

from .conftest import run, sql


@pytest.fixture
def q(sb):
    return SupabaseJobs(sb)


@pytest.fixture
def background(monkeypatch):
    async def noop(ctx):
        return None

    monkeypatch.setitem(KINDS, "index", Kind(noop, 30, "x", exclusive=False, priority=0))


def test_one_exclusive_job_per_user_but_background_work_is_free(q, user, background):
    run(q.create(user, "manga", {"text": "x"}, 4))
    with pytest.raises(Busy):
        run(q.create(user, "image", {}, 1))
    run(q.create(user, "index", {}, 1))
    run(q.create(user, "index", {}, 1))
    assert sql(f"select count(*) from public.jobs where user_id = '{user}'") == "3"


def test_dedupe_key_returns_the_job_already_there(q, user, dream, background):
    first = run(q.create(user, "index", {}, 1, dream_id=dream, dedupe_key=f"index:{dream}"))
    with pytest.raises(Duplicate) as dup:
        run(q.create(user, "index", {}, 1, dream_id=dream, dedupe_key=f"index:{dream}"))
    assert dup.value.job.id == first.id


def test_claim_takes_priority_first_then_age_and_skips_jobs_not_due(q, user, background):
    bg = run(q.create(user, "index", {}, 1))
    drawn = run(q.create(user, "image", {}, 1))
    later = run(q.create(user, "index", {}, 1))
    sql(f"update public.jobs set run_after = now() + interval '1 hour' where id = '{later.id}'")
    assert run(q.claim("w1", 60, 3)).id == drawn.id
    assert run(q.claim("w1", 60, 3)).id == bg.id
    assert run(q.claim("w1", 60, 3)) is None  # the last one waits for its run_after


def test_only_the_holding_worker_writes_and_a_stalled_job_is_taken_over(q, user):
    job = run(q.create(user, "image", {}, 1))
    claimed = run(q.claim("w1", 60, 3))
    assert claimed.id == job.id and claimed.attempts == 1
    assert run(q.update(job.id, {"done": 1}, worker="w1", lease=60))
    assert not run(q.update(job.id, {"done": 2}, worker="w2"))
    sql(f"update public.jobs set lease_until = now() - interval '1 second' where id = '{job.id}'")
    again = run(q.claim("w2", 60, 3))
    assert again.id == job.id and again.worker == "w2" and again.attempts == 2
    assert not run(q.update(job.id, {"done": 1}, worker="w1"))  # w1 lost it


def test_a_job_out_of_attempts_fails_for_good(q, user):
    job = run(q.create(user, "image", {}, 1))
    run(q.claim("w1", 60, 1))
    sql(f"update public.jobs set lease_until = now() - interval '1 second' where id = '{job.id}'")
    assert run(q.claim("w2", 60, 1)) is None
    assert sql(f"select status from public.jobs where id = '{job.id}'") == "failed"


def test_clients_see_no_jobs_even_when_there_are_some(q, user):
    run(q.create(user, "image", {}, 1))
    assert sql("set role anon; select count(*) from public.jobs;").splitlines()[-1] == "0"
    assert sql("select count(*) from public.jobs") == "1"


def test_jobs_of_a_dream_belong_to_their_owner(q, user, dream, background):
    run(q.create(user, "index", {}, 1, dream_id=dream))
    assert [j.kind for j in run(q.for_dream(user, dream))] == ["index"]
    other = "00000000-0000-4000-8000-000000000999"
    assert run(q.for_dream(other, dream)) == []


def test_deleting_the_dream_deletes_its_jobs(q, user, dream, background):
    run(q.create(user, "index", {}, 1, dream_id=dream))
    sql(f"delete from public.dreams where id = '{dream}'")
    assert sql(f"select count(*) from public.jobs where user_id = '{user}'") == "0"


@pytest.mark.parametrize("status,expected", [(503, "queued"), (422, "failed")])
def test_worker_backs_off_or_stops_on_the_real_queue(q, user, monkeypatch, status, expected):
    async def fails(ctx):
        raise ProviderError(f"fal: status {status}", status)

    monkeypatch.setitem(KINDS, "image", Kind(fails, 5, "çizim başarısız"))
    job = run(q.create(user, "image", {}, 1))
    w = worker.Worker(SimpleNamespace(queue=q, blobs=None))
    before = datetime.now(timezone.utc)
    run(w.run_one(run(q.claim(w.name, 60, 3))))
    row = sql(f"select status, run_after > now() + interval '2 seconds', error from public.jobs where id = '{job.id}'").split("|")
    assert row[0] == expected
    if expected == "queued":
        assert row[1] == "t" and row[2] == ""  # waits a few seconds before the next try
        assert run(q.claim("w2", 60, 3)) is None
    else:
        assert row[2] == "çizim başarısız"
    assert datetime.now(timezone.utc) - before < timedelta(seconds=10)
