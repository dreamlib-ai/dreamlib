import asyncio
from datetime import datetime, timezone

from app.store.jobstore import Job

from .conftest import ANALYSIS, OTHER, TOKEN, auth, storyboard, wait_job

DREAM = {**ANALYSIS, "originalText": "Ormanın üstünde uçuyordum.", "type": "cultural", "mood": "huzurlu", "sleep": "iyi"}


def test_dreams_need_accounts_and_a_token(api):
    client, _ = api
    assert client.get("/api/dreams").status_code == 401
    assert client.get("/api/dreams", headers=auth("short")).status_code == 401


def test_save_list_get_delete(api):
    client, _ = api
    res = client.post("/api/dreams", headers=auth(), json=DREAM)
    assert res.status_code == 201
    saved = res.json()
    assert saved["visibility"] == "private" and saved["style"] == "manga" and saved["sleep"] == "iyi"
    assert saved["panels"] == [] and "manga_meta" not in saved and "jobId" not in saved

    assert client.get("/api/dreams", headers=auth()).json()["dreams"][0]["id"] == saved["id"]
    assert client.get(f"/api/dreams/{saved['id']}", headers=auth()).json()["title"] == "Uçan orman"
    assert client.get(f"/api/dreams/{saved['id']}", headers=auth(OTHER)).status_code == 404
    assert client.delete(f"/api/dreams/{saved['id']}", headers=auth(OTHER)).status_code == 404
    assert client.delete(f"/api/dreams/{saved['id']}", headers=auth()).status_code == 204
    assert client.get(f"/api/dreams/{saved['id']}", headers=auth()).status_code == 404


def test_save_rejects_bad_input(api):
    client, _ = api
    for patch in [
        {"originalText": ""}, {"title": ""}, {"type": "astrology"}, {"visibility": "friends"}, {"style": "pixel"},
        {"mood": "x" * 41}, {"tags": ["t"] * 21}, {"panels": [{"caption": "a", "path": "javascript:alert(1)"}]},
        {"panels": [{"caption": "a", "path": "https://x.example/a.png"}] * 10},
    ]:
        assert client.post("/api/dreams", headers=auth(), json={**DREAM, **patch}).status_code == 400, patch


def test_manga_job_makes_a_booklet_and_saves_with_its_drawing_plan(api):
    client, s = api
    s.llm.reply = storyboard(4)
    res = client.post("/api/manga", headers=auth(), json={"title": "Uçan orman", "text": "Uçuyordum.", "panels": 4})
    assert res.status_code == 202
    job = wait_job(client, res.json()["id"])
    assert job["status"] == "done" and job["done"] == 4 and len(job["panels"]) == 4
    assert job["panels"][1]["caption"] == "Sahne 1" and job["panels"][1]["url"].startswith("https://")

    # first panel from the text alone, the rest edited from it so the character stays the same
    assert [c[0] for c in s.images.calls] == ["generate"] and len(s.editor.calls) == 3
    assert all(c[2] == [job["panels"][0]["path"]] for c in s.editor.calls)

    assert client.get(f"/api/jobs/{job['id']}", headers=auth(OTHER)).status_code == 404
    saved = client.post("/api/dreams", headers=auth(), json={**DREAM, "jobId": job["id"], "style": "manga"}).json()
    assert [p["caption"] for p in saved["panels"]] == [f"Sahne {i}" for i in range(4)]

    # a saved panel can be redrawn from the stored plan even when the job cache is gone
    s.queue.jobs.clear()
    redo = client.post(f"/api/dreams/{saved['id']}/panels/2/redo", headers=auth())
    assert redo.status_code == 200 and redo.json()["caption"] == "Sahne 2"
    assert client.post(f"/api/dreams/{saved['id']}/panels/9/redo", headers=auth()).status_code == 400
    assert client.post(f"/api/dreams/{saved['id']}/panels/2/redo", headers=auth(OTHER)).status_code == 404


def test_manga_rejects_bad_input_and_a_second_running_job(api):
    client, s = api
    s.llm.reply = storyboard(4)
    assert client.post("/api/manga", headers=auth(), json={"text": ""}).status_code == 400
    assert client.post("/api/manga", headers=auth(), json={"text": "x", "style": "nope"}).status_code == 400
    assert client.post("/api/manga", headers=auth(), json={"text": "x", "panels": 5}).status_code == 400
    assert client.post("/api/manga", json={"text": "x"}).status_code == 401

    # a booklet already in the making, held by another worker
    s.queue.jobs["x"] = Job(id="x", user_id=TOKEN, kind="manga", status="running", worker="elsewhere", created_at=datetime.now(timezone.utc))
    assert client.post("/api/manga", headers=auth(), json={"text": "x"}).status_code == 429
    assert client.post("/api/dreams", headers=auth(), json=DREAM).status_code == 409


def test_manga_fails_on_a_short_storyboard(api):
    client, s = api
    s.llm.reply = storyboard(2)
    job_id = client.post("/api/manga", headers=auth(), json={"text": "x", "panels": 4}).json()["id"]
    job = wait_job(client, job_id)
    assert job["status"] == "failed" and "okunamadı" in job["error"]


def test_consistency_failure_does_not_silently_draw_a_different_character(api):
    client, s = api
    s.llm.reply = storyboard(4)
    s.editor.fail = True
    job_id = client.post("/api/manga", headers=auth(), json={"text": "x", "panels": 4}).json()["id"]
    assert wait_job(client, job_id)["status"] == "failed"
    assert len(s.images.calls) == 1  # only the first panel was ever generated from text

    s.editor.fail = False
    ok = client.post("/api/manga", headers=auth(), json={"text": "x", "consistent": False, "panels": 4}).json()["id"]
    assert wait_job(client, ok)["status"] == "done"
    assert len(s.images.calls) == 5  # without consistency every panel is its own generation


def test_redo_job_panel(api):
    client, s = api
    s.llm.reply = storyboard(4)
    job_id = client.post("/api/manga", headers=auth(), json={"text": "x", "panels": 4}).json()["id"]
    before = wait_job(client, job_id)["panels"]
    redo = client.post(f"/api/jobs/{job_id}/panels/0/redo", headers=auth())
    assert redo.status_code == 200 and redo.json()["path"] != before[0]["path"]
    after = client.get(f"/api/jobs/{job_id}", headers=auth()).json()["panels"]
    assert after[0]["path"] == redo.json()["path"] and after[1]["path"] == before[1]["path"]
    assert client.post(f"/api/jobs/{job_id}/panels/7/redo", headers=auth()).status_code == 400

    s.limits.limits = {"redo": (1, 1)}
    assert client.post(f"/api/jobs/{job_id}/panels/1/redo", headers=auth()).status_code == 200
    assert client.post(f"/api/jobs/{job_id}/panels/1/redo", headers=auth()).status_code == 429


def test_a_job_left_halfway_carries_on_without_paying_twice(api):
    """As after a restart: the storyboard, panel 0 and a queued request for panel 1 are in the state."""
    client, s = api
    meta = {"Style": "manga", "CharacterNote": "n", "Scenes": [f"scene {i}" for i in range(4)], "RefURL": "", "Consistent": True}
    state = {
        "meta": meta, "captions": [f"Sahne {i}" for i in range(4)], "paths": ["https://fal.example/p0.png", "", "", ""],
        "requests": {"1": {"urls": ["https://fal.example/p1.png"]}},
    }
    s.queue.jobs["half"] = Job(
        id="half", user_id=TOKEN, kind="manga", status="queued", input={"text": "x"}, state=state, done=1, total=4, attempts=1,
        created_at=datetime.now(timezone.utc),
    )
    s.wake()
    job = wait_job(client, "half")
    assert job["status"] == "done" and [p["path"] for p in job["panels"][:2]] == ["https://fal.example/p0.png", "https://fal.example/p1.png"]
    assert s.llm.system == ""  # no second storyboard
    assert s.images.calls == [] and len(s.editor.calls) == 2  # only panels 2 and 3 were asked for
    assert all(c[2] == ["https://fal.example/p0.png"] for c in s.editor.calls)


def test_daily_limit_is_smaller_for_guests_and_failed_jobs_are_free(api):
    client, s = api
    s.llm.reply = storyboard(4)
    s.daily_guest, s.daily_user = 1, 2
    guest = auth("dev-guest-someone")
    first = client.post("/api/manga", headers=guest, json={"text": "x"}).json()["id"]
    assert wait_job(client, first, headers=guest)["status"] == "done"
    assert s.queue.jobs[first].cost_usd == 0.04  # four panels at the fake price
    res = client.post("/api/manga", headers=guest, json={"text": "x"})
    assert res.status_code == 429 and "1 çizim" in res.json()["error"]

    s.queue.jobs[first].status = "failed"
    assert client.post("/api/manga", headers=guest, json={"text": "x"}).status_code == 202

    for _ in range(2):
        job = client.post("/api/manga", headers=auth(), json={"text": "x"}).json()["id"]
        wait_job(client, job)
    assert client.post("/api/manga", headers=auth(), json={"text": "x"}).status_code == 429


class FakeBlobs:
    def __init__(self):
        self.removed = []

    async def remove(self, paths):
        self.removed += paths


def test_saving_marks_the_job_and_the_sweep_keeps_saved_pictures(api):
    from datetime import timedelta

    from app.worker import sweep

    client, s = api
    s.llm.reply = storyboard(4)
    job_id = client.post("/api/manga", headers=auth(), json={"text": "x"}).json()["id"]
    wait_job(client, job_id)
    assert client.post("/api/dreams", headers=auth(), json={**DREAM, "jobId": job_id}).status_code == 201
    assert s.queue.jobs[job_id].state["saved"] is True
    assert client.post("/api/dreams", headers=auth(), json={**DREAM, "jobId": job_id}).status_code == 409

    old = datetime.now(timezone.utc) - timedelta(days=8)
    s.queue.jobs[job_id].created_at = old
    s.queue.jobs["lost"] = Job(id="lost", user_id=TOKEN, kind="image", status="done", state={"paths": ["u/a.png", "u/b.png"]}, created_at=old)
    s.queue.jobs["new"] = Job(id="new", user_id=TOKEN, kind="image", status="done", state={"paths": ["u/c.png"]}, created_at=datetime.now(timezone.utc))
    s.blobs = FakeBlobs()

    assert asyncio.run(sweep(s)) == 2
    assert s.blobs.removed == ["u/a.png", "u/b.png"]  # the saved booklet's pictures stay with the dream
    assert set(s.queue.jobs) == {"new"}
