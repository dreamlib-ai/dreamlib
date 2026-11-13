"""arXiv: dream-research papers.

export.arxiv.org (API, OAI-PMH) and arxiv.org/api are Disallow: / for all robots,
so discovery runs through OpenAlex (arXiv source S4306400194). Each paper's
abs page (allowed, Crawl-delay 15) gives the licence and whether an HTML full
text exists; we take the HTML full text when present, otherwise the PDF.

Run: backend/.venv/Scripts/python -m corpus.sources.arxiv [--discover-only]
"""

from __future__ import annotations

import json
import re
import sys
from urllib.parse import quote

from corpus.sources.scholarly_common import (
    MAILTO, Blocked, MetaTable, Polite, folder_bytes, inverted_to_text, norm_license,
    relevance, topic_tags,
)

SOURCE = "arxiv"
API = "https://api.openalex.org/works"
FILTER = ('locations.source.id:S4306400194,title_and_abstract.search:dreams|dreaming|dreamt|"dream report"|'
          '"dream reports"|"dream content"|nightmare|nightmares|"lucid dream"|"lucid dreaming"|oneiric')
SELECT = "id,doi,title,publication_year,ids,authorships,locations,abstract_inverted_index,keywords,primary_topic"
CONTEXT = re.compile(r"sleep|\brem\b|dream report|dream content|dream recall|dream journal|"
                     r"psycholog|neuro|conscious|lucid dream|oneir|psychoanaly|freud|jung|hypnagog|ptsd|"
                     r"dream diar|dreambank|dream narrative|dream interpretation|dream imagery", re.I)
DREAM_WORDS = re.compile(r"\b(dreams?|dreaming|dreamt|dreamed|lucid dream\w*|nightmares?)\b")
ML_NOISE = re.compile(r"reinforcement learning|world model|policy|text-to-|diffusion model|3d generation|privacy|"
                      r"dark matter|graph neural|attack", re.I)


def arxiv_relevant(title: str, abstract: str, kws: list[str]) -> bool:
    text = f"{title} {abstract}"
    if re.search(r"(Dreams?|Dreaming|Nightmares?|Lucid)", title, re.I) and re.search(
            r"sleep|rem|psycholog|dream report|dream content|lucid", text, re.I) and not ML_NOISE.search(text):
        return True
    if len(DREAM_WORDS.findall(text)) < 2 or not CONTEXT.search(text):
        return False
    if ML_NOISE.search(text) and not re.search(r"sleep|\brem\b|dream report", text, re.I):
        return False
    return relevance(title, abstract, kws)
ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:v\d+)?(?:\.pdf)?$")


def discover(p: Polite, table: MetaTable) -> None:
    # cursor paging needs an API key ("API key required for cursor paging"); basic page= paging does not
    page, more = 0, True
    while more and page < 10:
        url = f"{API}?filter={quote(FILTER, safe=':,|!/')}&per-page=200&select={SELECT}&page={page + 1}&mailto={MAILTO}"
        try:
            r = p.get(url, name=f"api/openalex_p{page:03d}.json", license="openalex-metadata-cc0",
                      rights_holder="OurResearch (OpenAlex), CC0")
        except Exception as e:
            print("discovery stopped:", e)
            break
        d = r.json()
        print(f"discovery page {page} count={d['meta']['count']} budget={r.headers.get('x-ratelimit-remaining')}")
        for w in d["results"]:
            aid = None
            for loc in w.get("locations") or []:
                for u in (loc.get("landing_page_url"), loc.get("pdf_url")):
                    m = ARXIV_ID.search(u or "")
                    if m:
                        aid = m.group(1)
                        break
                if aid:
                    break
            if not aid:
                continue
            title = w.get("title") or ""
            abstract = inverted_to_text(w.get("abstract_inverted_index"))
            kws = [k.get("display_name", "") for k in w.get("keywords") or []]
            rel = arxiv_relevant(title, abstract, kws)
            old = table.get(aid) or {}
            table.put({
                "id": aid, "arxiv_id": aid, "openalex_id": w["id"].rsplit("/", 1)[-1],
                "title": title,
                "authors": [a["author"]["display_name"] for a in w.get("authorships") or [] if a.get("author")],
                "year": w.get("publication_year"),
                "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
                "primary_topic": (w.get("primary_topic") or {}).get("display_name"),
                "topic_tags": topic_tags(title, abstract), "relevant": rel, "abstract": abstract,
                "license": old.get("license"), "fulltext_path": old.get("fulltext_path"),
                "fulltext_status": old.get("fulltext_status"),
            })
        page += 1
        more = bool(d["results"]) and page * 200 < d["meta"]["count"]
        table.save()


def fetch_papers(p: Polite, table: MetaTable) -> None:
    for r in table.rows.values():
        r["relevant"] = arxiv_relevant(r.get("title") or "", r.get("abstract") or "", [])
    table.save()
    rows = [r for r in table.rows.values() if r.get("relevant")]
    print("relevant arXiv papers:", len(rows))
    for n, row in enumerate(rows):
        if row.get("fulltext_path"):
            continue
        aid = row["arxiv_id"]
        try:
            abs_url = f"https://arxiv.org/abs/{aid}"
            r = p.get(abs_url, name=f"abs/{aid.replace('/', '_')}.html", license="arxiv-abs-page",
                      rights_holder="arXiv / authors")
            html = r.text
            lic = re.search(r'href="(https?://(?:creativecommons\.org/(?:licenses|publicdomain)/[^"]+|arxiv\.org/licenses/[^"]+))"', html)
            row["license"] = norm_license(lic.group(1)) if lic else "unknown"
            row["license_url"] = lic.group(1) if lic else None
            vm = re.search(r'<meta name="citation_pdf_url" content="https?://arxiv\.org/pdf/([^"]+)"', html)
            ver = vm.group(1) if vm else aid
            hm = re.search(r'href="(https://arxiv\.org/html/[^"]+)"', html)
            safe = aid.replace("/", "_")
            if hm:
                url = hm.group(1)
                p.get(url, name=f"html/{safe}.html", license=row["license"], rights_holder="authors (arXiv)",
                      expect=("html",))
                row["fulltext_path"], row["fulltext_format"] = f"files/html/{safe}.html", "html"
            else:
                url = f"https://arxiv.org/pdf/{ver}"
                p.get(url, name=f"pdf/{safe}.pdf", license=row["license"], rights_holder="authors (arXiv)",
                      expect=("pdf",))
                row["fulltext_path"], row["fulltext_format"] = f"files/pdf/{safe}.pdf", "pdf"
            row["fulltext_url"] = url
            row["fulltext_status"] = "ok"
        except Blocked as e:
            row["fulltext_status"] = f"blocked: {e}"
        except Exception as e:
            row["fulltext_status"] = f"error: {type(e).__name__}: {str(e)[:150]}"
        table.save()
        print(f"{n+1}/{len(rows)} {aid} {row.get('license')} {row['fulltext_status']}", flush=True)


def main() -> None:
    p = Polite(SOURCE, base_delay=3.0, host_min={"api.openalex.org": 0.2, "arxiv.org": 15})
    table = MetaTable(SOURCE)
    if "--fetch-only" not in sys.argv:
        discover(p, table)
    if "--discover-only" not in sys.argv:
        fetch_papers(p, table)
    print("bytes", folder_bytes(SOURCE))
    print(json.dumps({"rows": len(table.rows)}))


if __name__ == "__main__":
    main()
