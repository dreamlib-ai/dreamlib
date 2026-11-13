"""Dream report datasets on Dryad (Fogli, Aiello, Quercia 2020 + API search).

Downloads via the Dryad API v2 (`/api/v2/files/<id>/download`; robots.txt only
blocks the web `/downloads` paths). Crawl-delay 5 is respected.

Run: backend/.venv/Scripts/python -m corpus.sources.dryad
"""

from __future__ import annotations

import json
from urllib.parse import quote

from corpus.fetch import Blocked, Fetcher, Meta

BASE = "https://datadryad.org"
FOGLI = "doi:10.5061/dryad.qbzkh18fr"
QUERIES = ["dream report", "dream reports", "dreams", "nightmare", "lucid dreaming", "dream content"]
DREAM_WORDS = ("dream", "nightmare", "oneir")
# Manually reviewed search hits: (note, kind). Anything not here and off-topic is dropped.
REVIEWED = {
    "doi:10.5061/dryad.r7sqv9scc": ("Aiello et al. Epidemic Dreams (COVID-19): only aggregated condition "
                                    "co-occurrence CSVs from 2,888 dream reports; no report texts.", "derived_aggregates"),
    "doi:10.7272/Q6P26WDC": ("REM eye-movement recordings (~70 GB), no dream report texts.", "other"),
}
OFF_TOPIC = {"doi:10.5061/dryad.n4h3672", "doi:10.5061/dryad.qrfj6q5zg", "doi:10.5061/dryad.k6djh9w6k",
             "doi:10.5061/dryad.kwh70rzbd", "doi:10.5061/dryad.hx3ffbghm", "doi:10.5061/dryad.tf7qr"}


def dataset(f: Fetcher, doi: str) -> dict:
    return f.get(f"{BASE}/api/v2/datasets/{quote(doi, safe='')}", save=False).json()


def files(f: Fetcher, ds: dict) -> list[dict]:
    href = ds["_links"]["stash:version"]["href"]
    return f.get(f"{BASE}{href}/files", save=False).json()["_embedded"]["stash:files"]


def main() -> None:
    f = Fetcher(Meta(source="dryad", license="CC0-1.0 (Dryad); text derived from DreamBank CC BY-NC-SA 4.0",
                     rights_holder="Fogli, Aiello, Quercia (Nokia Bell Labs / Imperial); reports: DreamBank"),
                delay=6.0, timeout=300)
    out = []

    ds = dataset(f, FOGLI)
    saved, total = [], 0
    for item in files(f, ds):
        url = BASE + item["_links"]["stash:download"]["href"]
        try:
            r = f.get(url, name=item["path"])
        except Blocked as e:
            print("blocked", url, e)
            continue
        saved.append(item["path"])
        total += len(r.content)
    rows = None
    tsv = f.dir / "files" / "rsos_dream_data.tsv"
    if tsv.exists():
        with tsv.open(encoding="utf-8", errors="replace") as fh:
            rows = sum(1 for _ in fh) - 1
    out.append(dict(
        name="Fogli et al. 2020 — Our Dreams, Our Selves (rsos_dream_data.tsv)",
        source=f"https://doi.org/{FOGLI.split(':', 1)[1]}", kind="real_reports", rows=rows,
        languages=["en"], license="CC0-1.0 (Dryad record)",
        upstream_license="DreamBank CC BY-NC-SA 4.0 (report texts)",
        rights_holder="Alessandro Fogli, Luca Maria Aiello, Daniele Quercia; reports © DreamBank (Schneider & Domhoff)",
        contact="see the Dryad dataset page", hvdc_coded=True, gated=False,
        downloaded=bool(saved), files=saved, bytes=total,
        note=("" if saved else "NOT DOWNLOADED: /api/v2/files/<id>/download returns 401 (token required), web "
              "/downloads is disallowed by robots.txt -> manual download by Cenker or API key. ") + "Automatic HVdC scores (characters, emotions, aggression/friendliness/sexuality) + raw text.",
    ))

    # Search for other dream datasets (list only; small ones downloaded if clearly dream reports).
    seen = {FOGLI}
    for q in QUERIES:
        try:
            r = f.get(f"{BASE}/api/v2/search?q={quote(q)}&per_page=50", save=False)
        except Exception as e:
            print("search failed", q, e)
            continue
        for d in r.json().get("_embedded", {}).get("stash:datasets", []):
            doi = d.get("identifier")
            title = d.get("title", "")
            text = (title + " " + (d.get("abstract") or "")[:2000]).lower()
            if doi in seen or doi in OFF_TOPIC or not any(w in text for w in DREAM_WORDS):
                continue
            note, kind = REVIEWED.get(doi, (f"Dryad search hit for '{q}'; review manually.", "candidate"))
            seen.add(doi)
            out.append(dict(
                name=title.strip(), source=f"https://doi.org/{doi.split(':', 1)[1]}", kind=kind,
                rows=None, languages=[], license=d.get("license", ""), upstream_license="",
                rights_holder="; ".join(f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                                        for a in d.get("authors", [])[:4]),
                contact="", hvdc_coded=False, gated=False, downloaded=False, files=[],
                bytes=0, note=f"{note} Size {d.get('storageSize')} B. API download needs a Dryad token (401).",
            ))
    with (f.dir / "datasets.jsonl").open("w", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps([(o["name"][:80], o["rows"], o["bytes"]) for o in out], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
