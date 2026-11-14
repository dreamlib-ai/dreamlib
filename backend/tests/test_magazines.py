"""G4: the magazine spec and the `magazine` job, on the in-memory stores."""
import time
from datetime import date, datetime, timezone

import pytest

from app.models import Dream, Panel
from app.pipelines.magazine import build, first_sentence
from app.store.magazines import MemoryMagazines

from .conftest import OTHER, auth, make_client, storyboard, wait_job
from .test_contract import check
from .test_dreams import DREAM


def dream(n: int, **kw) -> Dream:
    return Dream(id="d1", title="Uçan orman", originalText="Ham anlatım.", cleanText="", type="universal",
                 interpretation="Uçmak özgürlük isteğini anlatır. Orman ise bilinmeyendir.", style="manga",
                 tags=["uçmak", "orman"], emotions=[{"label": "Huzur", "pct": 60}, {"label": "Merak", "pct": 40},
                                                    {"label": "Korku", "pct": 0}],
                 panels=[Panel(caption=f"Sahne {i}", path=f"u/{i}.png") for i in range(n)],
                 createdAt=datetime(2026, 11, 10, 7, tzinfo=timezone.utc), **kw)


def test_layouts_follow_picture_shapes_and_the_quote_sits_in_the_middle():
    meta = {"u/0.png": {"width": 768, "height": 1024, "color": "#102343"},
            "u/1.png": {"width": 1536, "height": 1024}, "u/2.png": {"width": 1536, "height": 1024},
            "u/3.png": {"width": 1536, "height": 1024}}
    spec = build(dream(5), meta)  # u/4.png has no facts: square, full page
    assert [(p.layout, p.panels) for p in spec.pages] == [
        ("full", [0]), ("pair", [1, 2]), ("quote", []), ("wide", [3]), ("full", [4])]
    assert spec.pages[2].text == "Uçmak özgürlük isteğini anlatır."
    assert spec.cover.model_dump() == {"title": "Uçan orman", "panel": 0, "color": "#102343"}
    assert spec.colophon.dated == "2026-11-10" and spec.colophon.emotions == ["Huzur", "Merak"]
    assert [p.path for p in spec.panels] == [f"u/{i}.png" for i in range(5)]
    assert "Ham anlatım" not in spec.model_dump_json()  # the raw narration never goes into a magazine


def test_the_night_it_was_dreamt_wins_and_long_quotes_are_cut():
    spec = build(dream(1, journal={"dreamedOn": date(2026, 11, 1)}), {})
    assert spec.colophon.dated == "2026-11-01" and [p.layout for p in spec.pages] == ["full", "quote"]
    assert first_sentence("a" * 300).endswith("…") and len(first_sentence("a" * 300)) == 220
    assert first_sentence("") == ""


@pytest.fixture
def mag_api(monkeypatch):
    monkeypatch.setattr("app.worker.BACKOFF", (0, 0, 0))
    client, s = make_client(magazines=MemoryMagazines())
    with client:
        yield client, s


def magazine_jobs(s, dream_id):
    return [j for j in s.queue.jobs.values() if j.kind == "magazine" and j.dream_id == dream_id]


def wait_laid_out(s, dream_id, count=1, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        jobs = magazine_jobs(s, dream_id)
        if len(jobs) >= count and all(j.status == "done" for j in jobs):
            return jobs
        time.sleep(0.02)
    raise AssertionError(f"magazine jobs: {[(j.status, j.error) for j in magazine_jobs(s, dream_id)]}")


def test_a_saved_booklet_becomes_a_magazine_and_a_redrawn_panel_lays_it_out_again(mag_api):
    client, s = mag_api
    s.llm.reply = storyboard(4)
    job = wait_job(client, client.post("/api/v1/manga", headers=auth(), json={"title": "Uçan orman", "text": "Uçuyordum.",
                                                                              "panels": 4}).json()["id"])
    saved = client.post("/api/v1/dreams", headers=auth(), json={**DREAM, "jobId": job["id"], "style": "manga"}).json()
    wait_laid_out(s, saved["id"])
    res = client.get(f"/api/v1/dreams/{saved['id']}/magazine", headers=auth())
    assert res.status_code == 200
    mag = res.json()
    spec = client.app.openapi()
    check(spec, spec["components"]["schemas"]["MagazineOut"], mag)
    assert mag["dreamId"] == saved["id"] and mag["visibility"] == "private" and mag["status"] == "ready"
    assert [p["caption"] for p in mag["panels"]] == ["Sahne 0", "Sahne 1", "Sahne 2", "Sahne 3"]
    assert all(p["url"] for p in mag["panels"]) and mag["spec"]["cover"]["title"] == saved["title"]
    assert client.get(f"/api/v1/dreams/{saved['id']}/magazine", headers=auth(OTHER)).status_code == 404
    status = client.get(f"/api/v1/dreams/{saved['id']}/status", headers=auth()).json()
    assert "magazine" in [j["kind"] for j in status["jobs"]]

    assert client.post(f"/api/v1/dreams/{saved['id']}/panels/1/redo", headers=auth()).status_code == 200
    wait_laid_out(s, saved["id"], count=2)
    again = client.get(f"/api/v1/dreams/{saved['id']}/magazine", headers=auth()).json()
    assert again["id"] == mag["id"] and again["panels"][1]["path"] != mag["panels"][1]["path"]


def test_a_dream_without_pictures_has_no_magazine(mag_api):
    client, s = mag_api
    saved = client.post("/api/v1/dreams", headers=auth(), json=DREAM).json()
    assert magazine_jobs(s, saved["id"])  # queued all the same: it removes a magazine whose booklet is gone
    wait_laid_out(s, saved["id"])
    res = client.get(f"/api/v1/dreams/{saved['id']}/magazine", headers=auth())
    assert res.status_code == 404 and res.json()["code"] == "not_found"


def test_without_the_magazine_store_nothing_is_queued(api):
    client, s = api
    saved = client.post("/api/v1/dreams", headers=auth(), json=DREAM).json()
    assert not magazine_jobs(s, saved["id"])
    assert client.get(f"/api/v1/dreams/{saved['id']}/magazine", headers=auth()).status_code == 503
