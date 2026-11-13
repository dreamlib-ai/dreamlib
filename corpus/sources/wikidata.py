"""Wikidata entities for dream concepts and common dream symbols (concept alignment).

query.wikidata.org/sparql is disallowed by its robots.txt, so the script logs
that refusal and uses the public QLever Wikidata SPARQL endpoint
(qlever.cs.uni-freiburg.de, robots allows) for discovery, with a polite delay.
Full entity JSON comes from www.wikidata.org/wiki/Special:EntityData/<Q>.json
(robots allows). Output: files/entities/<Q>.json, files/qlever/*.json and
concepts.jsonl (labels, descriptions, aliases, sitelinks for 25 languages).
Wikidata has no dream meanings, so no entries.jsonl rows are produced.
License: Wikidata data is CC0.
"""

from __future__ import annotations

import json
import re
import time

import httpx
from urllib.parse import urlencode

from corpus.fetch import ROOT, Blocked, Fetcher, Meta

SOURCE = "wikidata"
LANGS = ["en", "tr", "ar", "fa", "ur", "he", "zh", "ja", "ko", "hi", "id", "vi", "th",
         "ru", "de", "fr", "es", "it", "pt", "pl", "el", "la", "sa", "bn", "sw"]
QLEVER = "https://qlever.cs.uni-freiburg.de/api/wikidata"
PREFIX = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
PREFIX wikibase: <http://wikiba.se/ontology#>
"""
# Verified on 2026-10-25 via EntityData / QLever label lookup.
SEEDS = {
    "Q36348": "dream", "Q192692": "nightmare", "Q181078": "lucid dream",
    "Q6028924": "daydream", "Q867634": "dream interpretation", "Q1640439": "oneiromancy",
    "Q1364020": "false awakening", "Q5306496": "dream dictionary", "Q1417053": "dream yoga",
    "Q336468": "dream journal", "Q4366501": "recurring dream", "Q1870591": "dream book",
    "Q6488379": "Category:Dream",
}
# Candidate symbol vocabulary chosen by us (common motifs in the Indian, Islamic,
# Chinese and Western dream books of this corpus); Wikidata has no "dream symbol" class.
SYMBOLS = """snake elephant lion bull cow horse dog cat bird fish crow owl eagle vulture pig donkey
camel monkey tiger wolf fox rat mouse spider bee scorpion frog turtle crocodile peacock swan goose
rooster dragon deer sheep goat buffalo
water river sea ocean lake rain flood fire flame smoke sun moon star sky cloud lightning thunder
wind storm mountain earthquake snow ice desert forest tree flower lotus fruit mango grape apple
garden field grain rice wheat milk honey butter curd meat bread wine egg salt oil
tooth hair blood head eye hand foot nail beard tongue heart skin
house temple mosque church palace door window roof wall ladder bridge road well grave cemetery
city market prison ship boat chariot cart
gold silver iron copper jewel pearl diamond coin money mirror ring necklace crown sword knife
bow arrow umbrella flag vase pot lamp book key clothes shoe garland throne bed
king queen priest monk god goddess angel demon ghost corpse mother father child baby
wedding marriage death funeral birth pregnancy flying falling swimming bathing nudity
eating vomiting weeping laughing dancing singing fighting war
white black red yellow green blue""".split()


def ql(f: Fetcher, name: str, sparql: str) -> list[dict]:
    url = QLEVER + "?" + urlencode({"query": PREFIX + sparql})
    local = ROOT / SOURCE / "files" / "qlever" / f"{name}.json"
    if f.seen(url) and local.exists():
        return json.loads(local.read_text(encoding="utf-8"))["results"]["bindings"]
    for attempt in range(4):
        try:
            time.sleep(10)  # QLever is a shared public service: one query at a time, slowly
            r = f.get(url, name=f"qlever/{name}.json")
            return r.json()["results"]["bindings"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429:
                raise
            if attempt == 3:
                print("QLever keeps returning 429; skipping query", name)
                return []
            time.sleep(60 * (attempt + 1))
    return []


def qid(b: dict, var: str = "item") -> str:
    return b[var]["value"].rsplit("/", 1)[-1]


def main() -> None:
    f = Fetcher(Meta(SOURCE, license="CC0 1.0", rights_holder="Wikidata contributors",
                     tradition="encyclopedic"), delay=1.0)
    # 1) Official endpoint: record the robots refusal.
    try:
        f.get("https://query.wikidata.org/sparql?query=" + "SELECT%20*%20WHERE%20%7B%7D", save=False)
    except Blocked as e:
        print("WDQS:", e)

    seeds = " ".join(f"wd:{q}" for q in SEEDS if not SEEDS[q].startswith("Category"))
    kinds: dict[str, set[str]] = {q: {"seed"} for q in SEEDS}

    def add(q: str, kind: str) -> None:
        if re.fullmatch(r"Q\d+", q):
            kinds.setdefault(q, set()).add(kind)

    rows = ql(f, "concepts", f"""SELECT DISTINCT ?item WHERE {{ VALUES ?s {{ {seeds} }}
      {{ ?item wdt:P31/wdt:P279* ?s }} UNION {{ ?item wdt:P279+ ?s }} UNION
      {{ ?item wdt:P361 ?s }} UNION {{ ?item wdt:P1269 ?s }} UNION {{ ?s wdt:P279 ?item }} UNION
      {{ ?s wdt:P361 ?item }} UNION {{ ?s wdt:P1269 ?item }} }}""")
    for b in rows:
        add(qid(b), "concept")
    rows = ql(f, "works", f"""SELECT DISTINCT ?item WHERE {{ VALUES ?s {{ {seeds} }}
      ?item wdt:P921 ?s . ?item wikibase:sitelinks ?sl . FILTER(?sl > 0) }}""")
    for b in rows:
        add(qid(b), "work_about_dreams")
    rows = ql(f, "categories", f"""SELECT DISTINCT ?item WHERE {{ VALUES ?s {{ {seeds} }}
      {{ ?item wdt:P301 ?s }} UNION {{ ?s wdt:P910 ?item }} }}""")
    for b in rows:
        add(qid(b), "wikipedia_category")

    # 2) Symbol candidates: the most-sitelinked item carrying the exact English label.
    vals = " ".join(f'"{s}"@en' for s in SYMBOLS)
    rows = ql(f, "symbols", f"""SELECT ?label ?item ?sl WHERE {{ VALUES ?label {{ {vals} }}
      ?item rdfs:label ?label . ?item wikibase:sitelinks ?sl . FILTER(?sl > 5) }}""")
    best: dict[str, tuple[int, str]] = {}
    for b in rows:
        lab, q, sl = b["label"]["value"], qid(b), int(b["sl"]["value"])
        if lab not in best or sl > best[lab][0]:
            best[lab] = (sl, q)
    symbol_of: dict[str, str] = {}
    for lab, (_, q) in best.items():
        add(q, "symbol_candidate")
        symbol_of[q] = lab

    print("entities:", len(kinds), "symbols matched:", len(best), "/", len(SYMBOLS))

    # 3) Full entity JSON + compact concept rows.
    out = ROOT / SOURCE / "concepts.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for q in sorted(kinds, key=lambda x: int(x[1:])):
            url = f"https://www.wikidata.org/wiki/Special:EntityData/{q}.json"
            try:
                data = f.get(url, name=f"entities/{q}.json").json()
            except Blocked as e:
                print("blocked", q, e)
                continue
            ent = next(iter(data["entities"].values()))
            claims = ent.get("claims", {})

            def vals_of(p: str) -> list[str]:
                res = []
                for c in claims.get(p, []):
                    v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
                    if isinstance(v, dict) and "id" in v:
                        res.append(v["id"])
                return res

            row = {
                "qid": ent.get("id", q),
                "kind": sorted(kinds[q]),
                "symbol_query_label": symbol_of.get(q, ""),
                "labels": {l: ent.get("labels", {}).get(l, {}).get("value", "") for l in LANGS},
                "descriptions": {l: ent.get("descriptions", {}).get(l, {}).get("value", "")
                                 for l in ("en", "tr")},
                "aliases": {l: [a["value"] for a in ent.get("aliases", {}).get(l, [])]
                            for l in ("en", "tr")},
                "sitelinks": {l: ent.get("sitelinks", {}).get(f"{l}wiki", {}).get("title", "")
                              for l in LANGS},
                "sitelink_count": len(ent.get("sitelinks", {})),
                "P31": vals_of("P31"), "P279": vals_of("P279"),
                "url": f"https://www.wikidata.org/wiki/{q}",
                "license": "CC0 1.0",
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
