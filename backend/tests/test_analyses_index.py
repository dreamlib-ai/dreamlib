"""M3 (analyses rows) and M4 (the no-LLM index job) through the API, on the in-memory stores."""
import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.pipelines.index import language, reading
from app.store.analyses import MemoryAnalyses
from app.store.entities import MemoryEntities

from .conftest import OTHER, auth, make_client
from .test_dreams import DREAM


@pytest.fixture
def lab_api(monkeypatch):
    monkeypatch.setattr("app.worker.BACKOFF", (0, 0, 0))
    client, s = make_client(analyses=MemoryAnalyses(), entities=MemoryEntities())
    with client:
        yield client, s


def index_jobs(s, dream_id):
    return [j for j in s.queue.jobs.values() if j.kind == "index" and j.dream_id == dream_id]


def wait_indexed(s, dream_id, count=1, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        jobs = index_jobs(s, dream_id)
        if len(jobs) >= count and all(j.status == "done" for j in jobs):
            return jobs
        time.sleep(0.02)
    raise AssertionError(f"index jobs: {[(j.status, j.error) for j in index_jobs(s, dream_id)]}")


def test_language_guess():
    assert language("Çok korktum ve kaçtım.") == "tr"
    assert language("I was in my old house and I was afraid.") == "en"
    assert language("Ormanda yürüdüm") == "tr"  # no Turkish letters, Turkish words


def test_reading_keeps_evidence_and_negations():
    out = reading("Hiç korkmadım ama çok şaşırdım. Rüyada olduğumu fark ettim.")
    assert [e["class"] for e in out["emotions"]] == ["confusion"]
    assert out["negated"][0]["class"] == "apprehension" and out["negated"][0]["word"] == "korkmadım"
    assert out["perspective"] == "first-person" and [e["kind"] for e in out["experiences"]] == ["lucid"]


def test_an_interpretation_is_a_row_and_the_saved_dream_takes_it(lab_api):
    client, s = lab_api
    analysis = client.post("/api/analyze", headers=auth(), json={"text": "Ormanda kayboldum ve çok korktum."}).json()
    aid = analysis["analysisId"]
    row = s.analyses.rows[0]
    assert row["id"] == aid and row["pipeline"] == "interpret" and row["prompt"].startswith("interpret@")
    assert row["dream_id"] is None and len(row["input_sha256"]) == 64 and "interpretation" in row["output"]

    dream = client.post("/api/dreams", headers=auth(), json={**DREAM, **analysis, "originalText": "Ormanda kayboldum ve çok korktum."}).json()
    assert "analysisId" not in dream
    assert row["dream_id"] == dream["id"]


def test_a_foreign_or_used_analysis_is_not_attached(lab_api):
    client, s = lab_api
    aid = client.post("/api/analyze", headers=auth(), json={"text": "Uçuyordum."}).json()["analysisId"]
    theirs = client.post("/api/dreams", headers=auth(OTHER), json={**DREAM, "analysisId": aid}).json()
    assert s.analyses.rows[0]["dream_id"] is None  # another account cannot take it
    mine = client.post("/api/dreams", headers=auth(), json={**DREAM, "analysisId": aid}).json()
    again = client.post("/api/dreams", headers=auth(), json={**DREAM, "analysisId": aid}).json()
    assert s.analyses.rows[0]["dream_id"] == mine["id"] != again["id"] and theirs["id"] != mine["id"]


def test_saving_indexes_the_dream_without_a_model(lab_api):
    client, s = lab_api
    calls = s.llm.calls if hasattr(s.llm, "calls") else None
    dream = client.post("/api/dreams", headers=auth(), json={**DREAM, "originalText": "Karanlık bir ormanda kayboldum. Çok korktum."}).json()
    wait_indexed(s, dream["id"])
    links = [l for l in s.entities.links if l["dream_id"] == dream["id"]]
    keys = {key for (kind, key), node in s.entities.nodes.items() if node["id"] in {l["entity_id"] for l in links}}
    assert keys == {"hvdc.apprehension"} and links[0]["quote"] == "korktum" and links[0]["extractor"] == "lab.emotions@1"
    row = next(r for r in s.analyses.rows if r["pipeline"] == "lab.index")
    assert row["dream_id"] == dream["id"] and row["prompt"] == "lab@1" and row["model"] == ""
    assert row["output"]["perspective"] == "first-person" and row["output"]["revision"] == dream["revision"]
    if calls is not None:
        assert s.llm.calls == calls  # indexing never calls the model


def test_editing_the_text_reindexes_and_replaces_old_links(lab_api):
    client, s = lab_api
    dream = client.post("/api/dreams", headers=auth(), json={**DREAM, "originalText": "Çok korktum."}).json()
    wait_indexed(s, dream["id"])
    edited = client.patch(f"/api/dreams/{dream['id']}/journal", headers=auth(),
                          json={"revision": dream["revision"], "originalText": "Çok mutluydum."}).json()
    wait_indexed(s, dream["id"], count=2)
    links = [l for l in s.entities.links if l["dream_id"] == dream["id"]]
    happy = s.entities.nodes[("emotion", "hvdc.happiness")]["id"]
    assert [l["entity_id"] for l in links] == [happy]  # the fear link of the old text is gone
    assert len([r for r in s.analyses.rows if r["pipeline"] == "lab.index"]) == 2 and edited["revision"] > dream["revision"]


def test_index_jobs_neither_block_nor_cost_the_user(lab_api):
    client, s = lab_api
    owner = asyncio.run(s.auth.user_id("dev-testuser-one"))
    dream = client.post("/api/dreams", headers=auth(), json=DREAM).json()
    asyncio.run(s.queue.create(owner, "index", {"dreamId": dream["id"]}, 1, dream_id=dream["id"], dedupe_key="held"))
    assert not asyncio.run(s.queue.active(owner))  # background work does not count as busy
    since = datetime.now(timezone.utc) - timedelta(days=1)
    assert asyncio.run(s.queue.count_since(owner, since)) == 0  # nor against the daily drawing limit
    again = client.post("/api/dreams", headers=auth(), json={**DREAM, "originalText": "Başka bir rüya."})
    assert again.status_code == 201  # the save lock is free while index jobs wait


def test_a_deleted_dream_is_skipped_not_failed(lab_api):
    client, s = lab_api
    dream = client.post("/api/dreams", headers=auth(), json=DREAM).json()
    wait_indexed(s, dream["id"])
    owner = asyncio.run(s.auth.user_id("dev-testuser-one"))
    assert client.delete(f"/api/dreams/{dream['id']}", headers=auth()).status_code == 204
    asyncio.run(s.queue.create(owner, "index", {"dreamId": dream["id"]}, 1, dedupe_key="after-delete"))
    client.post("/api/dreams", headers=auth(), json=DREAM)  # wakes the worker from its own loop (wake is not thread-safe)
    deadline = time.time() + 5
    while time.time() < deadline:
        job = next(j for j in s.queue.jobs.values() if j.dedupe_key == "after-delete")
        if job.status in ("done", "failed"):
            break
        time.sleep(0.02)
    assert job.status == "done" and job.state.get("skipped") == "dream deleted"
