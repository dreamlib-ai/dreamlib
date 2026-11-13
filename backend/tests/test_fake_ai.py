"""DREAMLIB_FAKE_AI=1 with DREAMLIB_DEV_AUTH=1 runs every paid feature locally without keys."""
import asyncio
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.providers.fake import FakeLLM, placeholder
from app.services import build_services

TOKEN = "dev-fake-ai-user"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def fake_settings(**kw) -> Settings:
    return replace(Settings(), dev_auth=True, fake_ai=True, workers=1, **kw)


def test_fake_ai_turns_every_provider_on():
    s = build_services(fake_settings())
    assert s.llm and s.images and s.editor and s.speech and s.queue


def test_fake_ai_refuses_a_real_database():
    with pytest.raises(SystemExit):
        build_services(fake_settings(supabase_url="https://x.supabase.co", supabase_service_key="k"))


def test_fake_llm_answers_each_task_in_shape():
    llm = FakeLLM()
    clean = asyncio.run(llm.chat([{"role": "system", "content": "Sen Dreamlib'in metin düzelticisisin."}, {"role": "user", "content": "  denizde  yüzüyordum "}]))
    assert '"cleanText": "Denizde yüzüyordum"' in clean
    board = asyncio.run(llm.chat([{"role": "system", "content": "Sen Dreamlib'in storyboard çizerisin. 6 panellik"}, {"role": "user", "content": "deniz ay"}]))
    assert board.count('"scene"') == 6


def test_placeholder_is_a_stable_svg_data_uri():
    assert placeholder("a") == placeholder("a") != placeholder("b")
    assert placeholder("a").startswith("data:image/svg+xml;base64,")


def test_whole_flow_runs_without_keys():
    with TestClient(create_app(build_services(fake_settings()))) as client:
        r = client.post("/api/analyze", json={"text": "Dün gece denizin kıyısında yürüyordum, gökyüzünde iki ay vardı."}, headers=AUTH)
        assert r.status_code == 200, r.text
        analysis = r.json()
        assert analysis["title"] and analysis["tags"]

        r = client.post("/api/manga", json={"title": analysis["title"], "text": analysis["cleanText"], "style": "manga", "panels": 4, "consistent": True}, headers=AUTH)
        assert r.status_code == 202, r.text
        job_id = r.json()["id"]
        for _ in range(100):
            job = client.get(f"/api/jobs/{job_id}", headers=AUTH).json()
            if job["status"] != "running":
                break
            time.sleep(0.05)
        assert job["status"] == "done", job
        assert len(job["panels"]) == 4

        r = client.post("/api/dreams", json={"title": analysis["title"], "originalText": analysis["cleanText"], "jobId": job_id}, headers=AUTH)
        assert r.status_code in (200, 201), r.text
        assert client.get("/api/dreams", headers=AUTH).json()
