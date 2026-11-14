"""`index` (M4): what a dream report states, read without a model, written as nodes and an analyses row.

Runs after a dream is saved or its text changes (app/indexing.py queues it). The no-LLM lab readers
(app/lab, docs/lab.md) take the narrative as the dreamer wrote it:
- emotions: the five Hall–Van de Castle classes stated in the text, each linked to an `emotion` node
  (hvdc.<class>) in `dream_entities` with the word that stated it;
- perspective and experience claims (lucid, recurring, nightmare, quoted word for word);
- the interpretation fields the dream already carries, `objects` and `features` (M8, app/pipelines/fields.py).
Everything, negated hits included, goes into one `analyses` row (pipeline lab.index) so a later reader can
see why. Vectors and neighbours come later (docs/gorevler.md, Sonraki major)."""
import re

from ..errors import NotFound
from ..lab.emotions import detect
from ..lab.experiences import claims
from ..lab.perspective import read
from ..store.entities import Link, Node
from .context import JobContext
from .fields import opened

FAILED = "rüya dizinlenemedi"
TIMEOUT = 60
LAB = "lab@1"  # the rule set; bump with the readers
EXTRACTOR = "lab.emotions@1"

EMOTIONS = {
    "anger": Node("emotion", "hvdc.anger", {"tr": "Öfke", "en": "Anger"}),
    "apprehension": Node("emotion", "hvdc.apprehension", {"tr": "Korku ve kaygı", "en": "Apprehension"}),
    "sadness": Node("emotion", "hvdc.sadness", {"tr": "Üzüntü", "en": "Sadness"}),
    "confusion": Node("emotion", "hvdc.confusion", {"tr": "Şaşkınlık", "en": "Confusion"}),
    "happiness": Node("emotion", "hvdc.happiness", {"tr": "Mutluluk", "en": "Happiness"}),
}
TR_LETTERS = re.compile(r"[çğışöüÇĞİŞÖÜ]")
TR_WORDS = re.compile(r"\b(ve|bir|bu|çok|ama|gibi|sonra|için|rüyamda|gördüm)\b", re.I)
EN_WORDS = re.compile(r"\b(the|and|was|my|i|dream|dreamed|dreamt)\b", re.I)


def language(text: str) -> str:
    """tr or en, from letters and very common words; Turkish when unsure (most reports are)."""
    if TR_LETTERS.search(text):
        return "tr"
    return "en" if len(EN_WORDS.findall(text)) > len(TR_WORDS.findall(text)) else "tr"


def reading(text: str) -> dict:
    """The lab readers' output for one narrative, with evidence."""
    lang = language(text)
    hits = detect(text, lang)
    stated: dict[str, dict] = {}
    for h in hits:
        if not h.negated and h.cls not in stated:
            stated[h.cls] = {"class": h.cls, "word": h.word, "start": h.start}
    persp = read(text, lang)
    return {
        "lang": lang,
        "emotions": list(stated.values()),
        "negated": [{"class": h.cls, "word": h.word, "start": h.start} for h in hits if h.negated],
        "perspective": persp.perspective,
        "perspectiveEvidence": {"firstPerson": persp.first_person[:10], "observer": persp.observer[:10]},
        "experiences": [{"kind": e.kind, "quote": e.quote} for e in claims(text)],
    }


async def run(ctx: JobContext) -> None:
    s, job = ctx.s, ctx.job
    dream_id = job.input.get("dreamId") or job.dream_id or ""
    try:
        d = await s.store.get_dream(job.user_id, dream_id)
    except NotFound:
        ctx.state["skipped"] = "dream deleted"  # nothing to index; not a failure the user should see
        return
    text = d.originalText
    out = reading(text)
    if s.entities and out["emotions"]:
        ids = await s.entities.ensure([EMOTIONS[e["class"]] for e in out["emotions"]])
        links = [Link(ids[EMOTIONS[e["class"]].key], 1.0, e["word"]) for e in out["emotions"]]
        await s.entities.link(d.id, EXTRACTOR, links)
    elif s.entities:
        await s.entities.link(d.id, EXTRACTOR, [])  # an edit removed the last stated emotion
    fields = opened(d, out["lang"])
    if s.entities:
        for (extractor, source), items in fields.items():
            ids: dict[str, str] = {}
            for status in ("approved", "candidate"):
                if nodes := [o.node for o in items if o.status == status]:
                    ids.update(await s.entities.ensure(nodes, status))
            await s.entities.link(d.id, extractor, [Link(ids[o.node.key], 1.0, o.quote) for o in items if o.node.key in ids], source)
    if s.analyses:
        await s.analyses.add(job.user_id, "lab.index", {**out, "revision": d.revision}, prompt=LAB,
                             input_text=text, dream_id=d.id)
    ctx.state["result"] = {"emotions": [e["class"] for e in out["emotions"]], "perspective": out["perspective"],
                           "experiences": [e["kind"] for e in out["experiences"]], "revision": d.revision,
                           "fields": {extractor: len(items) for (extractor, _), items in fields.items()}}
