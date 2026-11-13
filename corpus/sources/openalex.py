"""OpenAlex: metadata + OA locations for dream research (psychology, neuroscience,
medicine, humanities / anthropology of dreams), then CC-licensed full texts from
the OA locations that are not already covered by PMC (europepmc) or arXiv.

Run: backend/.venv/Scripts/python -m corpus.sources.openalex [--meta-only|--fulltext-only]

Without an API key OpenAlex gives a small shared daily budget; the harvest keeps
its cursor in state.json and resumes on the next run.
"""

from __future__ import annotations

import json
import sys
from urllib.parse import quote, urlparse

from corpus.sources.scholarly_common import (
    MAILTO, Blocked, MetaTable, Polite, folder_bytes, inverted_to_text, is_open_license,
    norm_license, relevance, topic_tags,
)

SOURCE = "openalex"
API = "https://api.openalex.org/works"
SELECT = ",".join([
    "id", "doi", "title", "publication_year", "publication_date", "ids", "language", "type",
    "primary_location", "open_access", "authorships", "biblio", "primary_topic", "topics",
    "keywords", "concepts", "mesh", "locations", "best_oa_location", "abstract_inverted_index",
    "cited_by_count", "is_retracted",
])
DREAM_T = "dream|dreams|dreaming|dreamt|nightmare|nightmares|oneiric"
QUERIES = [
    # (name, filter, sort, max_pages)
    ("psy_neuro_med",
     f"title.search:{DREAM_T},is_oa:true,primary_topic.field.id:fields/32|fields/28|fields/27|fields/36",
     "cited_by_count:desc", 60),
    ("humanities_social",
     'title.search:dreams|dreaming|dreamt|nightmares|oneiric|oneiromancy|"dream interpretation"|"dream book",'
     "is_oa:true,primary_topic.field.id:fields/12|fields/33,primary_topic.id:!T13161",
     "cited_by_count:desc", 30),
    ("anthropology_culture",
     'title_and_abstract.search:"anthropology of dreams"|"dream interpretation"|oneiromancy|"dream narratives"'
     '|"dream sharing"|"dream culture"|"dream books"|"dream divination",is_oa:true',
     "cited_by_count:desc", 8),
]
ARXIV_SOURCE = "https://openalex.org/S4306400194"
MIN_BUDGET = 180  # x-ratelimit-remaining units to leave untouched (~6 calls)


def harvest(p: Polite, table: MetaTable) -> None:
    state_path = p.dir / "state.json"
    state = json.loads(state_path.read_text("utf-8")) if state_path.exists() else {}
    for name, flt, sort, max_pages in QUERIES:
        st = state.setdefault(name, {"page": 0, "done": False})
        while not st["done"] and st["page"] < max_pages:
            url = (f"{API}?filter={quote(flt, safe=':,|!/')}&sort={sort}&per-page=200"
                   f"&select={SELECT}&page={st['page'] + 1}&mailto={MAILTO}")  # cursor paging needs a key
            try:
                r = p.get(url, name=f"api/{name}_p{st['page']:03d}.json",
                          license="openalex-metadata-cc0", rights_holder="OurResearch (OpenAlex), CC0")
            except Exception as e:  # bad query (400): next query; budget/auth/network: stop
                print(f"[{name}] stop: {e}")
                if " 400 " in str(e) or "400 Bad" in str(e):
                    st["done"], st["error"] = True, str(e)[:200]
                    state_path.write_text(json.dumps(state, indent=1), "utf-8")
                    break
                state_path.write_text(json.dumps(state, indent=1), "utf-8")
                return
            d = r.json()
            if st["page"] == 0:
                st["count"] = d["meta"]["count"]
            for w in d["results"]:
                add_work(table, w, name)
            st["page"] += 1
            if not d["results"] or st["page"] * 200 >= min(d["meta"]["count"], 10000):
                st["done"] = True
            state_path.write_text(json.dumps(state, indent=1), "utf-8")
            table.save()
            remaining = r.headers.get("x-ratelimit-remaining")
            print(f"[{name}] page {st['page']} / count {st.get('count')} works={len(table.rows)} budget={remaining}")
            if remaining is not None and float(remaining) < MIN_BUDGET:
                print("daily budget nearly used; resume tomorrow")
                return


def add_work(table: MetaTable, w: dict, query: str) -> None:
    wid = w["id"].rsplit("/", 1)[-1]
    abstract = inverted_to_text(w.get("abstract_inverted_index"))
    kws = [k.get("display_name", "") for k in (w.get("keywords") or [])]
    title = w.get("title") or ""
    locs = []
    for loc in w.get("locations") or []:
        src = loc.get("source") or {}
        locs.append({
            "landing": loc.get("landing_page_url"), "pdf": loc.get("pdf_url"),
            "license": norm_license(loc.get("license")), "version": loc.get("version"),
            "is_oa": loc.get("is_oa"), "source": src.get("display_name"), "source_id": src.get("id"),
            "source_type": src.get("type"),
        })
    best = w.get("best_oa_location") or {}
    old = table.get(wid) or {}
    pt = w.get("primary_topic") or {}
    table.put({
        "id": wid,
        "title": title,
        "authors": [a["author"]["display_name"] for a in w.get("authorships") or [] if a.get("author")],
        "year": w.get("publication_year"),
        "date": w.get("publication_date"),
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "pmid": (w.get("ids") or {}).get("pmid", "").rsplit("/", 1)[-1] or None,
        "pmcid": ((w.get("ids") or {}).get("pmcid") or "").rsplit("/", 1)[-1] or None,
        "type": w.get("type"),
        "language": w.get("language"),
        "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
        "license": norm_license(best.get("license")),
        "oa_status": (w.get("open_access") or {}).get("oa_status"),
        "oa_url": (w.get("open_access") or {}).get("oa_url"),
        "locations": locs,
        "primary_topic": pt.get("display_name"),
        "field": (pt.get("field") or {}).get("display_name"),
        "keywords": kws,
        "topic_tags": topic_tags(title, abstract, " ".join(kws)),
        "relevant": relevance(title, abstract, kws),
        "cited_by_count": w.get("cited_by_count"),
        "abstract": abstract,
        "queries": sorted(set(old.get("queries", [])) | {query}),
        "fulltext_path": old.get("fulltext_path"),
        "fulltext_status": old.get("fulltext_status"),
    })


def candidates(row: dict) -> list[dict]:
    out = []
    for loc in row.get("locations") or []:
        pdf = loc.get("pdf")
        if not pdf or not is_open_license(loc.get("license") or ""):
            continue
        if loc.get("source_id") == ARXIV_SOURCE or "arxiv.org" in pdf:
            continue  # arxiv.py handles these
        out.append(loc)
    out.sort(key=lambda l: (l.get("version") != "publishedVersion", "europepmc" in (l["pdf"] or "")))
    return out


def fulltext(p: Polite, table: MetaTable) -> None:
    rows = [r for r in table.rows.values() if r.get("relevant")]
    rows.sort(key=lambda r: -(r.get("cited_by_count") or 0))
    stats = {"ok": 0, "pmc": 0, "no_cc_pdf": 0, "blocked": 0, "failed": 0}
    for n, row in enumerate(rows):
        if row.get("fulltext_path"):
            stats["ok"] += 1
            continue
        if row.get("pmcid"):
            row["fulltext_status"] = "in-pmc (europepmc)"
            stats["pmc"] += 1
            continue
        locs = candidates(row)
        if not locs:
            row["fulltext_status"] = "no-cc-pdf-location"
            stats["no_cc_pdf"] += 1
            continue
        for loc in locs[:3]:
            url = loc["pdf"]
            host = urlparse(url).netloc
            if p.host_blocks.get(host, 0) >= 3:
                row["fulltext_status"] = f"host-skipped:{host}"
                continue
            try:
                p.get(url, name=f"pdf/{row['id']}.pdf", license=loc["license"],
                      rights_holder=loc.get("source") or "unknown", expect=("pdf",))
                row["fulltext_path"] = f"files/pdf/{row['id']}.pdf"
                row["fulltext_url"] = url
                row["fulltext_license"] = loc["license"]
                row["fulltext_status"] = "ok"
                p.host_blocks[host] = 0
                stats["ok"] += 1
                break
            except Blocked as e:
                p.host_blocks[host] = p.host_blocks.get(host, 0) + 1
                row["fulltext_status"] = f"blocked: {e}"
            except ValueError as e:  # html landing page / challenge instead of pdf
                p.host_blocks[host] = p.host_blocks.get(host, 0) + 1
                p.block(url, f"not-pdf: {str(e)[:120]}")
                row["fulltext_status"] = "not-pdf (landing/challenge page)"
            except Exception as e:
                row["fulltext_status"] = f"error: {type(e).__name__}: {str(e)[:120]}"
        if row.get("fulltext_status", "").startswith(("blocked", "not-pdf", "host-skipped")):
            stats["blocked"] += 1
        elif row.get("fulltext_status", "").startswith("error"):
            stats["failed"] += 1
        if n % 25 == 0:
            table.save()
            print(f"fulltext {n}/{len(rows)} {stats}", flush=True)
    table.save()
    print("fulltext done", stats)


def main() -> None:
    args = set(sys.argv[1:])
    p = Polite(SOURCE, base_delay=1.0, host_min={"api.openalex.org": 0.2, "zenodo.org": 10, "osf.io": 10})
    table = MetaTable(SOURCE)
    if "--fulltext-only" not in args:
        harvest(p, table)
    if "--meta-only" not in args:
        p.base_delay = 2.0
        fulltext(p, table)
    print("bytes", folder_bytes(SOURCE))


if __name__ == "__main__":
    main()
