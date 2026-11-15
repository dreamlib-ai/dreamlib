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
    assert text.startswith("A single full moon, drawn large") and "no frame" in text and "No text" in text
    assert "journal" not in text and "icon" not in text  # both words got drawn as text or as an app tile
    assert glyph_prompts.prompt("iron", key="sym.demir").startswith("A heavy bar of raw grey iron metal")
    assert glyph_prompts.LATEST == "glyph@3" and glyph_prompts.prompt("moon", "glyph@1").startswith("A small icon of moon")


def test_an_approved_symbol_gets_one_icon_and_others_get_none(glyph_api):
    client, s = glyph_api
    run = asyncio.run
    ids = run(s.entities.ensure([Node("symbol", "moon", {"tr": "Ay", "en": "moon"})], "approved"))
    cand = run(s.entities.ensure([Node("symbol", "door", {"tr": "Kapı"})], "candidate"))
    feel = run(s.entities.ensure([Node("emotion", "hvdc.anger", {"tr": "Öfke"})], "approved"))
    assert run(s.entities.without_glyph([*ids.values(), *cand.values(), *feel.values()], "glyph@3")) == [ids["moon"]]

    run(glyph.queue(s, "user-a", list(ids.values()) * 2))  # asked twice, queued once
    jobs = wait(s, "glyph")
    assert len(jobs) == 1 and jobs[0].status == "done"
    node = run(s.entities.get(ids["moon"]))
    assert node["glyph_path"] and node["glyph_path"] == jobs[0].state["glyphPath"] and node["glyph_prompt"] == "glyph@3"
    assert any("A single moon, drawn large" in str(call) for call in s.images.calls)

    run(glyph.queue(s, "user-b", [ids["moon"], cand["door"]]))  # someone else's dream: already drawn, never a candidate
    later = wait(s, "glyph", 3)
    assert sorted(j.state.get("skipped", "") for j in later if j.state.get("skipped")) == ["already drawn", "not an approved symbol"]


def test_an_icon_drawn_with_an_older_revision_is_drawn_again(glyph_api):
    client, s = glyph_api
    run = asyncio.run
    ids = run(s.entities.ensure([Node("symbol", "moon", {"en": "moon"})], "approved"))
    run(s.entities.set_glyph(ids["moon"], "https://x.test/old.webp", "glyph@2"))
    assert run(s.entities.without_glyph(list(ids.values()), "glyph@3")) == [ids["moon"]]
    run(glyph.queue(s, "user-a", list(ids.values())))
    jobs = wait(s, "glyph")
    assert jobs[0].status == "done" and not jobs[0].state.get("skipped")
    assert run(s.entities.get(ids["moon"]))["glyph_prompt"] == "glyph@3"


def test_a_pale_fill_inside_the_outline_is_kept():
    from PIL import ImageDraw
    img = Image.new("RGB", (1024, 1024), (246, 238, 222))
    draw = ImageDraw.Draw(img)
    draw.ellipse((200, 300, 824, 724), fill=(238, 228, 214), outline=(40, 60, 160), width=14)  # a pale loaf, outlined
    data = io.BytesIO()
    img.save(data, "PNG")
    out = Image.open(io.BytesIO(glyph.shrink(data.getvalue()))).convert("RGB")
    assert sum(abs(a - b) for a, b in zip(out.getpixel((128, 128)), glyph.CREAM)) > 12  # the loaf is not paper
    assert sum(abs(a - b) for a, b in zip(out.getpixel((2, 2)), glyph.CREAM)) < 12


def test_the_object_is_trimmed_to_fill_the_icon():
    paper = (246, 238, 222)
    img = Image.new("RGB", (1024, 1024), paper)
    img.paste((40, 60, 160), (400, 450, 560, 610))  # a small 160 px object in a wide margin
    data = io.BytesIO()
    img.save(data, "PNG")
    out = Image.open(io.BytesIO(glyph.shrink(data.getvalue()))).convert("RGB")
    assert out.size == (256, 256)
    dark = [x for x in range(256) if sum(out.getpixel((x, 128))) < 400]
    assert dark and dark[-1] - dark[0] > 200  # the object now spans most of the icon
    assert sum(abs(a - b) for a, b in zip(out.getpixel((2, 2)), glyph.CREAM)) < 12  # every icon gets the one cream


def test_a_card_inside_a_frame_is_peeled_to_the_object():
    img = Image.new("RGB", (1024, 1024), (20, 20, 20))  # a dark frame
    img.paste((236, 228, 220), (60, 60, 964, 964))  # a cream card a few shades off the paper
    img.paste((40, 60, 160), (420, 420, 600, 600))  # the object
    data = io.BytesIO()
    img.save(data, "PNG")
    out = Image.open(io.BytesIO(glyph.shrink(data.getvalue()))).convert("RGB")
    dark = [x for x in range(256) if sum(out.getpixel((x, 128))) < 400]
    assert dark[-1] - dark[0] > 200  # the object fills the icon, not the card
    for corner in ((1, 1), (254, 1), (1, 254), (254, 254)):
        assert sum(abs(a - b) for a, b in zip(out.getpixel(corner), glyph.CREAM)) < 12


def test_icons_are_kept_small():
    big = io.BytesIO()
    Image.new("RGB", (1024, 768), (40, 60, 120)).save(big, "PNG")
    small = Image.open(io.BytesIO(glyph.shrink(big.getvalue())))
    assert small.format == "WEBP" and max(small.size) == 256
