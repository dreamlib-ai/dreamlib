"""Internet Archive: public-domain dream books (OCR text + small PDFs).

Uses the advancedsearch API for dream-book subjects/titles in several languages,
keeps only items published 1929 or earlier (or explicitly marked public domain)
that are not access-restricted, then downloads each item's OCR full text
(_djvu.txt) and, when under 200 MB, its PDF. Every request goes through Fetcher.

Run from repo root:  backend/.venv/Scripts/python -m corpus.sources.internet_archive
Options: --no-pdf (text only), --parse-only (re-extract entries from saved OCR)
"""

from __future__ import annotations

import json
import re
import sys
from urllib.parse import quote

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "internet-archive"
MAX_YEAR = 1929
PDF_LIMIT = 200 * 1024 * 1024
SEARCH = "https://archive.org/advancedsearch.php"
FIELDS = ["identifier", "title", "date", "year", "creator", "language", "rights", "licenseurl",
          "possible-copyright-status", "access-restricted-item", "collection", "item_size", "subject",
          "publisher"]

QUERIES = [
    'subject:dreams', 'subject:"dream interpretation"', 'subject:"fortune-telling by dreams"',
    'subject:oneiromancy', 'subject:"dream books"', 'subject:"fortune-telling"',
    'subject:Traum', 'subject:Träume', 'subject:Traumdeutung', 'subject:rêves', 'subject:songes',
    'subject:sueños', 'subject:sogni', 'subject:dromen', 'subject:сны', 'subject:сонники',
    'title:"dream book"', 'title:"dream-book"', 'title:dreambook', 'title:"dream dictionary"',
    'title:"interpretation of dreams"', 'title:"book of dreams"', 'title:(dreams AND (fortune OR meaning OR interpreter OR dictionary OR oracle))',
    'title:"clef des songes"', 'title:(songes AND (clef OR explication OR interprétation OR interpretation))',
    'title:onirocritie', 'title:traumbuch', 'title:traumdeutung', 'title:traumbüchlein',
    'title:sonnik', 'title:сонник', 'title:"libro dei sogni"', 'title:(sogni AND (libro OR smorfia OR interpretazione OR spiegazione))',
    'title:smorfia', 'title:"libro de los sueños"', 'title:droomboek', 'title:drömbok', 'title:drømmebog',
    'title:unikirja', 'title:sennik', 'title:snář', 'title:álmoskönyv', 'title:tabirname', 'title:tabirnâme',
    'title:"tabir-i rüya"', 'title:"book of fate"', 'title:"napoleon\'s oraculum"', 'title:oraculum',
    'title:(onirocritica OR oneirocritica OR oneirocriticon OR artemidori OR artemidorus)',
]


def search(f: Fetcher, q: str) -> list[dict]:
    full = f"({q}) AND mediatype:texts"
    out, page = [], 1
    while True:
        url = (f"{SEARCH}?q={quote(full)}&" + "&".join(f"fl[]={x}" for x in FIELDS)
               + f"&rows=500&page={page}&output=json")
        data = f.get(url, save=False).json()["response"]
        out.extend(data["docs"])
        if page * 500 >= data["numFound"]:
            return out
        page += 1


def as_list(v) -> list:
    return v if isinstance(v, list) else ([] if v is None else [v])


def year_of(doc: dict) -> int | None:
    # year/date first; the imprint (publisher field, e.g. "London : J. Smith, 1850") as fallback.
    for k in ("year", "date", "publisher"):
        for v in as_list(doc.get(k)):
            m = re.search(r"\b(1[4-9]\d\d|20\d\d)\b", str(v))
            if m:
                return int(m.group(1))
    return None


def pd_status(doc: dict) -> tuple[bool, str]:
    rights = " ".join(str(x) for x in as_list(doc.get("rights")) + as_list(doc.get("possible-copyright-status")))
    lic = " ".join(as_list(doc.get("licenseurl")))
    cols = {c.lower() for c in as_list(doc.get("collection"))}
    if str(doc.get("access-restricted-item", "")).lower() == "true" or cols & {"inlibrary", "printdisabled", "lendinglibrary"}:
        return False, "access-restricted (lending/print-disabled)"
    if re.search(r"all rights reserved|in copyright|copyrighted|permission", rights, re.I) and not re.search(r"public domain|no known copyright|not in copyright", rights, re.I):
        return False, f"rights field: {rights[:120]}"
    y = year_of(doc)
    # Uploader-applied PD marks are not trusted on their own: a publication year is required.
    if y is None:
        return False, "no publication date"
    if y > MAX_YEAR:
        return False, f"published {y} (> {MAX_YEAR})"
    return True, f"published {y} (<= {MAX_YEAR}, US public domain)"


def collect(f: Fetcher) -> dict[str, dict]:
    items: dict[str, dict] = {}
    for q in QUERIES:
        try:
            docs = search(f, q)
        except Blocked as e:
            print("blocked search", q, e)
            continue
        print(f"{len(docs):5d}  {q}")
        for d in docs:
            ident = d["identifier"]
            if ident in items:
                items[ident]["queries"].append(q)
                continue
            d["queries"] = [q]
            items[ident] = d
    return items


def pick_files(meta: dict) -> tuple[dict | None, dict | None]:
    files = meta.get("files", [])
    txt = next((x for x in files if x["name"].endswith("_djvu.txt")), None)
    pdfs = [x for x in files if x["name"].lower().endswith(".pdf")]
    pdfs.sort(key=lambda x: (x.get("format") != "Text PDF", int(x.get("size", 0) or 0)))
    return txt, (pdfs[0] if pdfs else None)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    want_pdf = "--no-pdf" not in sys.argv
    parse_only = "--parse-only" in sys.argv
    base = ROOT / SOURCE
    f = Fetcher(Meta(source=SOURCE, license="public domain (pre-1930 US publication)", rights_holder="public domain"), delay=1.0, timeout=300.0)
    items_path = base / "items.jsonl"

    if not parse_only:
        found = collect(f)
        kept, skipped = [], []
        for ident, d in found.items():
            ok, why = pd_status(d)
            d["pd_basis"] = why
            d["year_parsed"] = year_of(d)
            (kept if ok else skipped).append(d)
        print("found", len(found), "kept", len(kept), "skipped", len(skipped))
        with (base / "skipped.jsonl").open("w", encoding="utf-8") as out:
            for d in skipped:
                out.write(json.dumps({k: d.get(k) for k in ("identifier", "title", "date", "year", "rights", "pd_basis", "queries")}, ensure_ascii=False) + "\n")

        # Pass 1: metadata + OCR text for every kept item.
        for i, d in enumerate(kept):
            ident = d["identifier"]
            try:
                mresp = f.get(f"https://archive.org/metadata/{ident}", name=f"{ident}/{ident}_meta.json", save=not f.seen(f"https://archive.org/metadata/{ident}"))
                meta = mresp.json()
            except Blocked as e:
                d["blocked"] = str(e)
                continue
            except Exception as e:
                d["error"] = repr(e)
                continue
            md = meta.get("metadata", {})
            d["rights_meta"] = md.get("rights", "")
            d["licenseurl_meta"] = md.get("licenseurl", "")
            if str(md.get("access-restricted-item", "")).lower() == "true":
                d["skip"] = "access-restricted (metadata)"
                continue
            txt, pdf = pick_files(meta)
            d["txt_file"] = txt["name"] if txt else None
            d["pdf_file"] = pdf["name"] if pdf else None
            d["pdf_size"] = int(pdf.get("size", 0) or 0) if pdf else 0
            f.meta.license = f"public domain; basis: {d['pd_basis']}"
            if txt:
                url = f"https://archive.org/download/{ident}/{quote(txt['name'])}"
                try:
                    f.get(url, name=f"{ident}/{txt['name']}")
                    d["txt_path"] = f"files/{ident}/{txt['name']}"
                except Blocked as e:
                    d["txt_blocked"] = str(e)
                except Exception as e:
                    d["txt_error"] = repr(e)
            print(f"[{i + 1}/{len(kept)}] {ident} txt={'y' if txt else 'n'} pdf={d['pdf_size'] // 1048576}MB")
        with items_path.open("w", encoding="utf-8") as out:
            for d in kept:
                out.write(json.dumps(d, ensure_ascii=False) + "\n")

        # Pass 2: PDFs under the size limit.
        if want_pdf:
            for i, d in enumerate(kept):
                if not d.get("pdf_file") or d.get("skip") or d["pdf_size"] >= PDF_LIMIT:
                    continue
                ident = d["identifier"]
                url = f"https://archive.org/download/{ident}/{quote(d['pdf_file'])}"
                if f.seen(url):
                    d["pdf_path"] = f"files/{ident}/{d['pdf_file']}"
                    continue
                f.meta.license = f"public domain; basis: {d['pd_basis']}"
                try:
                    f.get(url, name=f"{ident}/{d['pdf_file']}")
                    d["pdf_path"] = f"files/{ident}/{d['pdf_file']}"
                    print(f"pdf [{i + 1}/{len(kept)}] {ident} {d['pdf_size'] // 1048576}MB")
                except Blocked as e:
                    d["pdf_blocked"] = str(e)
                except Exception as e:
                    d["pdf_error"] = repr(e)
            with items_path.open("w", encoding="utf-8") as out:
                for d in kept:
                    out.write(json.dumps(d, ensure_ascii=False) + "\n")

    extract(base, items_path)


def extract(base, items_path) -> None:
    from corpus.sources.gutenberg import parse_generic

    entries = base / "entries.jsonl"
    if entries.exists():
        entries.unlink()
    total, counts = 0, {}
    for line in items_path.open(encoding="utf-8"):
        d = json.loads(line)
        if not d.get("txt_path"):
            continue
        p = base / d["txt_path"]
        if not p.is_file():
            continue
        lang = " ".join(as_list(d.get("language"))).lower()
        text = p.read_text(encoding="utf-8", errors="replace")
        rows = parse_generic(text, lang)
        if not rows:
            continue
        author = "; ".join(as_list(d.get("creator")))
        for r in rows:
            r.update({
                "source": SOURCE,
                "url": f"https://archive.org/details/{d['identifier']}",
                "license": f"public domain; {d.get('pd_basis', '')}",
                "rights_holder": "public domain",
                "attributed_author": author,
                "locator": f"{d['identifier']}; {r.get('locator', '')}",
            })
        write_entries(SOURCE, rows)
        counts[d["identifier"]] = len(rows)
        total += len(rows)
    (base / "entry_counts.json").write_text(json.dumps(counts, indent=1, ensure_ascii=False), encoding="utf-8")
    print("entries", total, "from", len(counts), "items")


if __name__ == "__main__":
    main()
