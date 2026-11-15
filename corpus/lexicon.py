"""M6: the first A-tier lexicon export (docs/veri.md, Hazırlık hattı step 5).

Joins the dream-book chapters of public-domain / CC0 sources to Wikidata symbol concepts (CC0) and writes
`corpus/lexicon/lexicon-a.jsonl`, the processed lexicon that may live in the public repo. One row per
(chapter, symbol): the symbol's Wikidata id and labels, the chapter heading and text word for word, where it is
and under which licence. Nothing from B or C sources goes in, and no meaning is rewritten.

First export: Artemidorus, Oneirocritica, English 1644 (EEBO-TCP, CC0). A chapter is joined to every symbol its
heading names (at most three), in old or modern spelling; chapters naming none are left out and counted.
Symbols without a Turkish Wikidata label are left out too: the product speaks Turkish.

A heading match is only a candidate: `curation-a.json` holds the pairs a person read and approved, keyed
"<locator>|<symbol key>", each with a short Turkish summary of what the chapter says about that symbol
(`meaning_tr`). Unapproved pairs (a heading that names a word the chapter is not about, "hog bristles" for the
pig) are left out and listed, so a new candidate is read before it reaches a dream's interpretation.

Run from the repo root after corpus.sources.artemidorus and corpus.sources.wikidata:
    backend/.venv/Scripts/python -m corpus.lexicon
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from corpus.fetch import ROOT

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.pipelines.fields import slug  # noqa: E402  the same node keys the index job opens

OUT = Path(__file__).with_name("lexicon") / "lexicon-a.jsonl"
CURATION = OUT.with_name("curation-a.json")
SOURCES = [("artemidorus", "en", "CC0")]  # (source, language, licence prefix that marks the A tier)
MAX_MEANING = 1500
MAX_SYMBOLS = 3
VAGUE = {"body", "case", "step", "vessel", "vessels", "instrument"}  # Wikidata aliases too broad for old chapter heads
IRREGULAR = {"teeth": "tooth", "children": "child", "feet": "foot", "mice": "mouse", "geese": "goose", "men": "man",
             "women": "woman", "oxen": "bull", "kine": "cow", "wolves": "wolf", "knives": "knife", "leaves": "tree"}


def concepts() -> dict[str, dict]:
    """English word -> concept, for the symbol candidates that have a Turkish label."""
    out: dict[str, dict] = {}
    for line in (ROOT / "wikidata" / "concepts.jsonl").open(encoding="utf-8"):
        c = json.loads(line)
        word = c.get("symbol_query_label", "")
        if "symbol_candidate" not in c["kind"] or not word or not c["labels"].get("tr"):
            continue
        for name in [word, *(a for a in c["aliases"].get("en", []) if " " not in a and a.lower() not in VAGUE)]:
            out.setdefault(name.lower(), c)
    return out


def words(heading: str) -> list[str]:
    """The heading's words with old spellings and plurals folded towards the modern singular."""
    out = []
    for w in re.findall(r"[a-z]+(?:-[a-z]+)*", heading.lower()):
        if "-" in w:  # rain-bow, earth-quake: one word, never its halves
            w = w.replace("-", "")
        forms = [IRREGULAR.get(w, w)]
        for cut in ("es", "s", "e"):
            if w.endswith(cut) and len(w) > len(cut) + 2:
                forms.append(w[: -len(cut)])
        out.append(forms)
    return out


def build() -> tuple[list[dict], int, int, list[str]]:
    known = concepts()
    approved: dict[str, str] = json.loads(CURATION.read_text(encoding="utf-8"))
    rows, chapters, unmatched, unread = [], 0, 0, []
    for source, lang, tier in SOURCES:
        for line in (ROOT / source / "entries.jsonl").open(encoding="utf-8"):
            e = json.loads(line)
            if e["language"] != lang or not e["license"].startswith(tier) or not e["meaning"].strip():
                continue
            chapters += 1
            found: list[dict] = []
            for forms in words(e["symbol_raw"]):
                c = next((known[f] for f in forms if f in known), None)
                if c and c not in found:
                    found.append(c)
            if not found:
                unmatched += 1
                continue
            for c in found[:MAX_SYMBOLS]:
                tr = c["labels"]["tr"]
                pair = f"{e.get('locator', '')}|sym.{slug(tr)}"
                if pair not in approved:
                    unread.append(f"{pair}  {e['symbol_raw'].strip()}")
                    continue
                rows.append({
                    "key": f"sym.{slug(tr)}", "qid": c["qid"], "labels": {"tr": tr, "en": c["labels"].get("en", "")},
                    "aliases_tr": [a for a in c["aliases"].get("tr", []) if slug(a)][:8],
                    "tradition": e["tradition"], "language": lang, "heading": e["symbol_raw"].strip(),
                    "meaning": " ".join(e["meaning"].split())[:MAX_MEANING], "meaning_tr": approved[pair],
                    "source": source,
                    "locator": e.get("locator", ""), "url": e.get("url", ""), "license": e["license"],
                    "rights_holder": e.get("rights_holder", ""), "attributed_author": e.get("attributed_author", ""),
                })
    return rows, chapters, unmatched, unread


def main() -> None:
    rows, chapters, unmatched, unread = build()
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    symbols = {r["key"] for r in rows}
    print(f"{chapters} chapters, {chapters - unmatched} joined, {unmatched} name no known symbol; "
          f"{len(rows)} rows, {len(symbols)} symbols -> {OUT}")
    if unread:
        print(f"{len(unread)} candidate pairs are not in {CURATION.name} and were left out:")
        print("\n".join("  " + u for u in unread))


if __name__ == "__main__":
    main()
