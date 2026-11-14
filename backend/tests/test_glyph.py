"""G1: one icon per approved symbol node, drawn once for everyone, with the fixed style template."""
import asyncio
import io
import time

import pytest
from PIL import Image

from app.pipelines import glyph
from app.prompts import glyph as glyph_prompts
from app.store.entities import MemoryEntities, Node

from .conftest import make_client


@pytest.fixture
def glyph_api(monkeypatch):
    monkeypatch.setattr("app.worker.BACKOFF", (0, 0, 0))
    client, s = make_client(entities=MemoryEntities())
    with client:
        yield client, s


def wait(s, kind, count=1, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        jobs = [j for j in s.queue.jobs.values() if j.kind == kind]
        if len(jobs) >= count and all(j.status in ("done", "failed") for j in jobs):
            return jobs
        time.sleep(0.02)
    raise AssertionError("glyph jobs did not finish")


def test_the_template_names_the_symbol_and_keeps_the_style_fixed():
    text = glyph_prompts.prompt("  full\nmoon ")
    assert text.startswith("A small icon of full moon for a dream journal") and "no text" in text
    assert glyph_prompts.REVISIONS["glyph@1"] == glyph_prompts.REVISIONS[glyph_prompts.LATEST]


def test_an_approved_symbol_gets_one_icon_and_others_get_none(glyph_api):
    client, s = glyph_api
    run = asyncio.run
    ids = run(s.entities.ensure([Node("symbol", "moon", {"tr": "Ay", "en": "moon"})], "approved"))
    cand = run(s.entities.ensure([Node("symbol", "door", {"tr": "Kapı"})], "candidate"))
    feel = run(s.entities.ensure([Node("emotion", "hvdc.anger", {"tr": "Öfke"})], "approved"))
    assert run(s.entities.without_glyph([*ids.values(), *cand.values(), *feel.values()])) == [ids["moon"]]

    run(glyph.queue(s, "user-a", list(ids.values()) * 2))  # asked twice, queued once
    jobs = wait(s, "glyph")
    assert len(jobs) == 1 and jobs[0].status == "done"
    node = run(s.entities.get(ids["moon"]))
    assert node["glyph_path"] and node["glyph_path"] == jobs[0].state["glyphPath"]
    assert any("A small icon of moon" in str(call) for call in s.images.calls)

    run(glyph.queue(s, "user-b", [ids["moon"], cand["door"]]))  # someone else's dream: already drawn, never a candidate
    later = wait(s, "glyph", 3)
    assert sorted(j.state.get("skipped", "") for j in later if j.state.get("skipped")) == ["already drawn", "not an approved symbol"]


def test_icons_are_kept_small():
    big = io.BytesIO()
    Image.new("RGB", (1024, 768), (40, 60, 120)).save(big, "PNG")
    small = Image.open(io.BytesIO(glyph.shrink(big.getvalue())))
    assert small.format == "WEBP" and max(small.size) == 256
