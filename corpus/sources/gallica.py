"""Gallica (BnF): public-domain "clés des songes".

Queries the Gallica SRU API for dream-key titles restricted to free-access
(public-domain) documents, then fetches the OCR text (texteBrut) of each hit.
Everything goes through Fetcher; if robots.txt or the server refuses (Gallica
sits behind a Cloudflare challenge for non-browser clients), the refusal is
logged in blocked.jsonl and the script stops without working around it.

Run from repo root:  backend/.venv/Scripts/python -m corpus.sources.gallica
"""

from __future__ import annotations

import json
import re
import sys
from urllib.parse import quote

from corpus.fetch import ROOT, Blocked, Fetcher, Meta

SOURCE = "gallica"
SRU = "https://gallica.bnf.fr/SRU?operation=searchRetrieve&version=1.2&maximumRecords=50&startRecord={start}&query={q}"
QUERIES = [
    'gallica all "clef des songes" and dc.type all "monographie" and access all "fayes"',
    'gallica all "clé des songes" and access all "fayes"',
    'dc.title all "songes" and dc.subject all "rêves" and access all "fayes"',
    'dc.subject all "oniromancie" and access all "fayes"',
    'dc.title all "interprétation des songes" and access all "fayes"',
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    base = ROOT / SOURCE
    f = Fetcher(Meta(source=SOURCE, license="Gallica public domain (BnF conditions: non-commercial reuse free, commercial reuse needs licence)",
                     rights_holder="Bibliothèque nationale de France (digitisation)"), delay=3.0)
    arks: dict[str, str] = {}
    status = {"blocked": [], "queries": {}}
    for q in QUERIES:
        url = SRU.format(start=1, q=quote(q))
        try:
            r = f.get(url, save=False)
        except Blocked as e:
            status["blocked"].append({"url": url, "reason": str(e)})
            print("blocked:", e)
            break  # host refuses us; do not keep hammering it
        except Exception as e:
            status["queries"][q] = repr(e)
            continue
        found = re.findall(r"(ark:/12148/[a-z0-9]+)", r.text)
        status["queries"][q] = len(set(found))
        for ark in found:
            arks.setdefault(ark, q)
    for ark in arks:
        url = f"https://gallica.bnf.fr/{ark}.texteBrut"
        try:
            f.get(url, name=ark.replace("/", "_") + ".html")
        except Blocked as e:
            status["blocked"].append({"url": url, "reason": str(e)})
            break
        except Exception as e:
            status["blocked"].append({"url": url, "reason": repr(e)})
    status["arks"] = list(arks)
    (base / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
