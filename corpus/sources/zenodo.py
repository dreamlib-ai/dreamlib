"""Zenodo dream report datasets (Mallett 2026 and mirrors). Files via /records/<id>/files/<name>.

Run: backend/.venv/Scripts/python -m corpus.sources.zenodo
"""
from __future__ import annotations
import json
from urllib.parse import quote
from corpus.fetch import Blocked, Fetcher, Meta

# id, name, kind, languages, hvdc, upstream note
RECORDS = [
    ("19161757", "A large corpus of lucid and non-lucid dream reports (DreamViews forum posts)", "real_reports", ["en"], False, "dreamviews.com forum posts; CC BY-NC 4.0"),
    ("18159468", "DreamBank raw HTML archive (Mallett)", "real_reports", ["en", "de"], False, "upstream DreamBank CC BY-NC-SA 4.0"),
    ("18076716", "Sleep and Dream Database (SDDb) full mirror (Mallett)", "real_reports", ["en"], False, "upstream SDDb terms unknown"),
    ("18089278", "krank data: hvdc (Hall & Van de Castle corpus from DreamBank)", "real_reports", ["en"], True, "upstream DreamBank CC BY-NC-SA 4.0"),
    ("18091505", "krank data: urbina1975", "real_reports", ["en"], False, "upstream DreamBank"),
    ("18099365", "krank data: ucsc1996", "real_reports", ["en"], False, "upstream DreamBank"),
    ("23582333", "Dream Symbol Frequencies, State of Dreams Fall 2026 (DreamEvaluator)", "derived_aggregates", ["en"], False, "aggregate counts only"),
]
LISTED = [("19040637", "Source data for: large corpus of lucid and non-lucid dream reports", "files restricted (request access) -> negotiation list"),
          ("18707459", "Corpus of Premonitory Dreams/Contacts (PDF of tweets)", "PDF of public tweets, not downloaded (X ToS, privacy)")]

def main() -> None:
    f = Fetcher(Meta(source="zenodo"), delay=10.0, timeout=600)
    out = []
    for rid, name, kind, langs, hvdc, note in RECORDS:
        d = f.get(f"https://zenodo.org/records/{rid}/export/json", save=False).json()
        m = d["metadata"]
        lic = [r["id"] for r in m.get("rights", [])]
        creators = "; ".join(c["person_or_org"]["name"] for c in m.get("creators", []))
        saved, total = [], 0
        for key in d["files"]["entries"]:
            url = f"https://zenodo.org/records/{rid}/files/{quote(key)}?download=1"
            try:
                r = f.get(url, name=f"{rid}/{key}")
            except Blocked as e:
                print("blocked", url, e); continue
            saved.append(key); total += len(r.content)
        rows = None
        for key in saved:
            if key.endswith((".csv", ".tsv")):
                with (f.dir / "files" / rid / key).open(encoding="utf-8", errors="replace") as fh:
                    rows = (rows or 0) + sum(1 for _ in fh) - 1  # lines, multi-line cells overcount
        out.append(dict(name=name, source=f"https://doi.org/{m.get('doi', '10.5281/zenodo.' + rid)}", kind=kind,
                        rows=rows, languages=langs, license=",".join(lic), upstream_license=note,
                        rights_holder=creators, contact="zenodo.org/records/" + rid, hvdc_coded=hvdc,
                        gated=False, downloaded=bool(saved), files=saved, bytes=total,
                        note="rows = csv/tsv line count (approximate)"))
        print(rid, rows, total)
    for rid, name, note in LISTED:
        out.append(dict(name=name, source=f"https://zenodo.org/records/{rid}", kind="real_reports", rows=None,
                        languages=[], license="", upstream_license="", rights_holder="", contact="",
                        hvdc_coded=False, gated=True, downloaded=False, files=[], bytes=0, note=note))
    with (f.dir / "datasets.jsonl").open("w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
