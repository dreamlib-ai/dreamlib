import asyncio
import time

from app.pipelines.registry import KINDS, Kind

from .conftest import OTHER, auth
from .test_dreams import DREAM


def test_one_address_shows_every_job_of_a_dream(api, monkeypatch):
    client, s = api
    release = asyncio.Event()

    async def index(ctx):  # a background job that waits until the test lets it finish
        while not release.is_set():
            await asyncio.sleep(0.01)

    monkeypatch.setitem(KINDS, "index", Kind(index, 5, "x", exclusive=False, priority=0))
    dream = client.post("/api/v1/dreams", headers=auth(), json=DREAM).json()
    status = client.get(f"/api/v1/dreams/{dream['id']}/status", headers=auth()).json()
    assert status["dreamId"] == dream["id"] and [j["kind"] for j in status["jobs"]] == ["index"]  # saving queues the index job

    owner = asyncio.run(s.auth.user_id("dev-testuser-one"))
    first = asyncio.run(s.queue.create(owner, "index", {}, 1, dream_id=dream["id"]))
    asyncio.run(s.queue.create(owner, "index", {}, 1, dream_id=dream["id"], parent_id=first.id))
    s.wake()

    status = client.get(f"/api/v1/dreams/{dream['id']}/status", headers=auth()).json()
    assert status["busy"] and [j["kind"] for j in status["jobs"]] == ["index", "index", "index"]
    assert status["jobs"][2]["parentId"] == first.id

    assert client.get(f"/api/v1/dreams/{dream['id']}/status", headers=auth(OTHER)).status_code == 404

    release.set()
    deadline = time.time() + 5
    while time.time() < deadline:
        status = client.get(f"/api/v1/dreams/{dream['id']}/status", headers=auth()).json()
        if not status["busy"]:
            break
        time.sleep(0.02)
    assert [j["status"] for j in status["jobs"]] == ["done", "done", "done"]
