import asyncio
import random

import httpx
import pytest

from app import eta
from app.eta import Estimator, MemoryTimings, RecursiveRidge, features
from app.providers import fal as fal_module
from app.providers.fal import Fal
from app.providers.image_models import resolve


def run(coro):
    return asyncio.run(coro)


def truth(x):  # 3 s base, 2 s a picture, 4 s a reference, 1.5 s a queue place
    return 3 + 2 * x[1] + 4 * x[2] + 1.5 * x[3]


def sample(rng):
    return features(rng.choice([1, 1, 2, 4]), rng.choice([0, 0, 1]), rng.randint(0, 6))


def test_prior_answers_before_any_data():
    assert RecursiveRidge(prior=[7.0, 0, 0, 0]).predict(features(1)) == 7.0


def test_curve_refits_until_its_error_is_low():
    rng = random.Random(1)
    curve = RecursiveRidge(prior=[10.0, 0, 0, 0])
    for _ in range(60):
        x = sample(rng)
        curve.update(x, truth(x) * rng.uniform(0.95, 1.05))
    assert curve.error < eta.TARGET_ERROR and curve.forgetting == eta.SETTLED
    x = features(2, 1, 3)
    assert abs(curve.predict(x) - truth(x)) / truth(x) < 0.15


def test_a_slower_provider_is_followed_and_the_curve_settles_again():
    rng = random.Random(2)
    curve = RecursiveRidge(prior=[10.0, 0, 0, 0])
    for _ in range(60):
        x = sample(rng)
        curve.update(x, truth(x))
    adapting_seen = False
    for _ in range(80):  # fal gets twice as slow
        x = sample(rng)
        curve.update(x, 2 * truth(x))
        adapting_seen |= curve.forgetting == eta.ADAPTING
    assert adapting_seen and curve.error < eta.TARGET_ERROR
    x = features(1, 0, 2)
    assert abs(curve.predict(x) - 2 * truth(x)) / (2 * truth(x)) < 0.15


def test_penalty_keeps_one_outlier_from_swinging_the_estimate():
    curve = RecursiveRidge(prior=[5.0, 0, 0, 0])
    curve.update(features(1), 120.0)  # one stuck request
    assert curve.predict(features(1)) < 60


def test_estimator_replays_stored_timings_after_a_restart():
    store = MemoryTimings()
    first = Estimator(store)
    rng = random.Random(3)
    for _ in range(40):
        x = sample(rng)
        run(first.observe("m", 10.0, x, truth(x), None))
    again = Estimator(store)  # a new process
    x = features(2, 0, 1)
    assert abs(run(again.estimate("m", 10.0, x)) - truth(x)) / truth(x) < 0.2


def test_fal_times_only_requests_it_queued_and_reads_the_queue_position(monkeypatch):
    monkeypatch.setattr(fal_module, "POLL_EVERY", 0)
    polls = {"n": 0}

    def handler(req: httpx.Request):
        if req.method == "POST":
            return httpx.Response(200, json={"status_url": "https://q/s", "response_url": "https://q/r"})
        if req.url.path == "/s":
            polls["n"] += 1
            if polls["n"] == 1:
                return httpx.Response(200, json={"status": "IN_QUEUE", "queue_position": 2})
            return httpx.Response(200, json={"status": "COMPLETED", "metrics": {"inference_time": 3.4}})
        return httpx.Response(200, json={"images": [{"url": "https://img/1"}]})

    store = MemoryTimings()
    client = Fal("key", resolve("fast", "image"))
    client.eta = Estimator(store)
    client.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def go():
        handle = await client.submit(Fal.image_body("koala"))
        await client.images(handle)
        polls["n"] = 1
        await client.images(handle)  # read again after a restart: not timed

    run(go())
    assert len(store.rows) == 1
    row = store.rows[0]
    assert row["model"] == "fal-ai/flux/schnell" and row["features"] == [1.0, 1.0, 0.0, 2.0]
    assert row["inference_seconds"] == 3.4 and row["total_seconds"] >= 0


def test_without_an_estimator_the_typical_time_is_used():
    client = Fal("key", resolve("quality", "image"))
    assert run(client.estimate(2)) == 24.0


@pytest.mark.parametrize("consistent,expected", [(True, 2 + 2), (False, 2 + 2)])
def test_booklet_estimate_counts_panel_one_then_batches(consistent, expected):
    from types import SimpleNamespace

    from app.models import MangaMeta
    from app.pipelines.manga import booklet_seconds
    from tests.conftest import FakeFal

    s = SimpleNamespace(images=FakeFal(), editor=FakeFal())
    assert run(booklet_seconds(s, MangaMeta(consistent=consistent), 4)) == expected  # 1 + ceil(3/3) panels
