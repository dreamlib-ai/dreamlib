"""`magazine` (G4): a saved booklet becomes a magazine the reader draws (docs/uretim.md, Dergi).

No model and no picture is paid for: the job lays out the panels the dream already has. The cover reuses the
first panel with the title and its dominant colour; pages take named layouts chosen from each picture's shape
(G3 sizes); a quote page carries the interpretation's first sentence; the colophon closes it. The raw narration
is never in the spec, so a shared magazine (G6) shows only captions and the reading.
Queued whenever a dream with panels is saved, edited or gets a redrawn panel (app/indexing.py)."""
import logging
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..errors import NotFound
from ..models import Dream
from .context import JobContext

log = logging.getLogger("dreamlib")

FAILED = "dergi hazırlanamadı"
TIMEOUT = 60
VERSION = 1
WIDE = 1.2  # width / height from which a picture is laid out across the page
QUOTE_MAX = 220

OUT = ConfigDict(json_schema_serialization_defaults_required=True)
Layout = Literal["full", "wide", "pair", "quote"]  # the client knows how to draw each; adding one is client work


class MagazinePanel(BaseModel):
    model_config = OUT
    path: str
    caption: str


class MagazineCover(BaseModel):
    model_config = OUT
    title: str
    panel: int  # index into the magazine's panels
    color: str  # dominant colour of that picture, '' when unknown


class MagazinePage(BaseModel):
    model_config = OUT
    layout: Layout
    panels: list[int] = []  # indexes; empty on a quote page
    text: str = ""  # the quote


class MagazineColophon(BaseModel):
    model_config = OUT
    dated: str  # YYYY-MM-DD: the night it was dreamt, else the day it was saved
    style: str
    tags: list[str]
    emotions: list[str]


class MagazineSpec(BaseModel):
    model_config = OUT
    version: int = VERSION
    cover: MagazineCover
    pages: list[MagazinePage]
    colophon: MagazineColophon
    panels: list[MagazinePanel]


def first_sentence(text: str) -> str:
    text = " ".join(text.split())
    match = re.match(r"(.+?[.!?…])(\s|$)", text)
    sentence = match.group(1) if match else text
    return sentence if len(sentence) <= QUOTE_MAX else sentence[: QUOTE_MAX - 1].rstrip() + "…"


def build(d: Dream, meta: dict[str, dict]) -> MagazineSpec:
    """The spec of one dream; `meta` is path -> G3 facts (width, height, color) for the pictures that have them."""
    def ratio(i: int) -> float:
        m = meta.get(d.panels[i].path)
        return m["width"] / m["height"] if m and m.get("height") else 1.0

    pages: list[MagazinePage] = []
    i, n = 0, len(d.panels)
    while i < n:
        if ratio(i) >= WIDE and i + 1 < n and ratio(i + 1) >= WIDE:
            pages.append(MagazinePage(layout="pair", panels=[i, i + 1]))
            i += 2
        else:
            pages.append(MagazinePage(layout="wide" if ratio(i) >= WIDE else "full", panels=[i]))
            i += 1
    if quote := first_sentence(d.interpretation):
        pages.insert(max(1, len(pages) // 2), MagazinePage(layout="quote", text=quote))
    cover = meta.get(d.panels[0].path, {}) if d.panels else {}
    dated = d.journal.dreamedOn.isoformat() if d.journal.dreamedOn else (d.createdAt.date().isoformat() if d.createdAt else "")
    felt = [e.label for e in sorted(d.emotions, key=lambda e: -e.pct) if e.pct > 0][:3]
    return MagazineSpec(
        cover=MagazineCover(title=d.title, panel=0, color=cover.get("color", "")),
        pages=pages,
        colophon=MagazineColophon(dated=dated, style=d.style, tags=d.tags[:6], emotions=felt),
        panels=[MagazinePanel(path=p.path, caption=p.caption) for p in d.panels],
    )


async def run(ctx: JobContext) -> None:
    s, job = ctx.s, ctx.job
    dream_id = job.input.get("dreamId") or job.dream_id or ""
    if not s.magazines:
        ctx.state["skipped"] = "magazines off"
        return
    try:
        d = await s.store.get_dream(job.user_id, dream_id)
    except NotFound:
        ctx.state["skipped"] = "dream deleted"
        return
    if not d.panels:
        await s.magazines.remove(job.user_id, d.id)  # the booklet was taken away
        ctx.state["skipped"] = "no panels"
        return
    meta: dict[str, dict] = {}
    if s.blobs and hasattr(s.blobs, "image_meta"):
        try:
            meta = await s.blobs.image_meta([p.path for p in d.panels])
        except Exception:
            log.warning("magazine: picture facts unavailable for %s", d.id, exc_info=True)
    spec = build(d, meta)
    ctx.state["magazineId"] = await s.magazines.put(job.user_id, d.id, spec.model_dump(mode="json"),
                                                    d.panels[spec.cover.panel].path, d.revision)
    job.done = 1
