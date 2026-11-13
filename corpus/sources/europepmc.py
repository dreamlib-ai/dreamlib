"""Europe PMC: open-access dream research articles (CC licences only) with full text.

Discovery: Europe PMC REST search (title/abstract/keyword hits, OPEN_ACCESS:Y).
Full text: NCBI's PMC Article Datasets on AWS (s3 pmc-oa-opendata: JATS XML +
plain text + licence json), the bulk channel NCBI provides for programmatic
use; eutils/ftp.ncbi are robots-disallowed. Articles not in that bucket fall
back to Europe PMC fullTextXML (www.ebi.ac.uk, robots Crawl-delay 10 honoured).

Run: backend/.venv/Scripts/python -m corpus.sources.europepmc [--search-only]
"""

from __future__ import annotations

import re
import sys
from urllib.parse import quote

from corpus.sources.scholarly_common import (
    Blocked, MetaTable, Polite, folder_bytes, is_open_license, norm_license, relevance,
    strip_tags, topic_tags,
)

SOURCE = "europepmc"
REST = "https://www.ebi.ac.uk/europepmc/webservices/rest"
S3 = "https://pmc-oa-opendata.s3.amazonaws.com"
FIELDS = ["dream*", "nightmare*", "oneiric", '"sleep paralysis"', '"lucid dreaming"']
QUERY = "(" + " OR ".join(f"{f}:{t}" for t in FIELDS for f in ("TITLE", "ABSTRACT", "KW")) + ") AND OPEN_ACCESS:Y"


def search(p: Polite, table: MetaTable) -> None:
    cursor, page = "*", 0
    while True:
        url = (f"{REST}/search?query={quote(QUERY)}&format=json&resultType=core&pageSize=1000"
               f"&cursorMark={quote(cursor)}")
        r = p.get(url, name=f"search/page_{page:03d}.json", license="europepmc-api-metadata",
                  rights_holder="Europe PMC (metadata); abstracts (c) publishers/authors")
        d = r.json()
        res = d.get("resultList", {}).get("result", [])
        print(f"search page {page} hits={d.get('hitCount')} got={len(res)}", flush=True)
        for a in res:
            add(table, a)
        table.save()
        nxt = d.get("nextCursorMark")
        if not res or not nxt or nxt == cursor:
            break
        cursor, page = nxt, page + 1


def add(table: MetaTable, a: dict) -> None:
    key = a.get("pmcid") or f"{a.get('source')}:{a.get('id')}"
    title = strip_tags(a.get("title", ""))
    abstract = strip_tags(a.get("abstractText", ""))
    kws = (a.get("keywordList") or {}).get("keyword", [])
    mesh = [m.get("descriptorName", "") for m in (a.get("meshHeadingList") or {}).get("meshHeading", [])]
    ji = a.get("journalInfo") or {}
    old = table.get(key) or {}
    table.put({
        "id": key,
        "pmcid": a.get("pmcid"), "pmid": a.get("pmid"), "epmc_id": a.get("id"), "epmc_source": a.get("source"),
        "doi": a.get("doi"),
        "title": title,
        "authors": [x.get("fullName") for x in (a.get("authorList") or {}).get("author", []) if x.get("fullName")],
        "year": int(a["pubYear"]) if str(a.get("pubYear", "")).isdigit() else None,
        "journal": (ji.get("journal") or {}).get("title") or (a.get("bookOrReportDetails") or {}).get("publisher"),
        "pub_types": (a.get("pubTypeList") or {}).get("pubType", []),
        "language": a.get("language"),
        "license_epmc": norm_license(a.get("license")),
        "license": old.get("license") or norm_license(a.get("license")),
        "keywords": kws, "mesh": mesh,
        "topic_tags": topic_tags(title, abstract, " ".join(kws), " ".join(mesh)),
        "relevant": relevance(title, abstract, kws + mesh),
        "in_epmc": a.get("inEPMC"), "in_pmc": a.get("inPMC"), "has_pdf": a.get("hasPDF"),
        "cited_by_count": a.get("citedByCount"),
        "abstract": abstract,
        "fulltext_path": old.get("fulltext_path"), "fulltext_status": old.get("fulltext_status"),
        "text_path": old.get("text_path"),
    })


def s3_latest(p: Polite, pmcid: str) -> str | None:
    r = p.get(f"{S3}/?list-type=2&prefix={pmcid}.&delimiter=/", save=False)
    vers = re.findall(rf"<Prefix>({pmcid}\.(\d+))/</Prefix>", r.text)
    if not vers:
        return None
    return max(vers, key=lambda v: int(v[1]))[0]


def fetch_one(p: Polite, row: dict) -> None:
    pmcid = row.get("pmcid")
    lic = row["license_epmc"]
    if pmcid:
        ver = s3_latest(p, pmcid)
        if ver:
            meta = p.get(f"{S3}/{ver}/{ver}.json", name=f"pmc/{pmcid}/{ver}.json", license=lic,
                         rights_holder="NCBI PMC metadata").json()
            lic = norm_license(meta.get("license_code")) if meta.get("license_code") else lic
            row["license"] = lic
            row["pmc_version"] = ver
            row["is_retracted"] = meta.get("is_retracted")
            if not is_open_license(lic):
                row["fulltext_status"] = f"skipped: licence {lic} (PMC)"
                return
            rh = row.get("journal") or "authors/publisher"
            if meta.get("xml_url"):
                p.get(f"{S3}/{ver}/{ver}.xml", name=f"pmc/{pmcid}/{ver}.xml", license=lic, rights_holder=rh)
                row["fulltext_path"] = f"files/pmc/{pmcid}/{ver}.xml"
            if meta.get("text_url"):
                p.get(f"{S3}/{ver}/{ver}.txt", name=f"pmc/{pmcid}/{ver}.txt", license=lic, rights_holder=rh)
                row["text_path"] = f"files/pmc/{pmcid}/{ver}.txt"
            if not row.get("fulltext_path") and meta.get("pdf_url"):
                p.get(f"{S3}/{ver}/{ver}.pdf", name=f"pmc/{pmcid}/{ver}.pdf", license=lic, rights_holder=rh,
                      expect=("pdf",))
                row["fulltext_path"] = f"files/pmc/{pmcid}/{ver}.pdf"
            row["fulltext_status"] = "ok (pmc-aws)" if row.get("fulltext_path") else "no-files (pmc-aws)"
            return
    # fallback: Europe PMC full text (PMC ids and some preprints)
    fid = pmcid or (row["epmc_id"] if row.get("epmc_source") == "PPR" else None)
    if not fid or row.get("in_epmc") != "Y":
        row["fulltext_status"] = "no-fulltext-source"
        return
    try:
        p.get(f"{REST}/{fid}/fullTextXML", name=f"epmc/{fid}.xml", license=lic,
              rights_holder=row.get("journal") or "authors/publisher", expect=("xml",))
        row["fulltext_path"] = f"files/epmc/{fid}.xml"
        row["fulltext_status"] = "ok (epmc)"
    except Exception as e:
        row["fulltext_status"] = f"epmc-fail: {type(e).__name__}: {str(e)[:100]}"


def fetch_all(p: Polite, table: MetaTable) -> None:
    rows = [r for r in table.rows.values() if r.get("relevant") and is_open_license(r.get("license_epmc", ""))]
    print("relevant + CC:", len(rows), "of", len(table.rows))
    for n, row in enumerate(rows):
        if row.get("fulltext_path") or (row.get("fulltext_status") or "").startswith("skipped"):
            continue
        try:
            fetch_one(p, row)
        except Blocked as e:
            row["fulltext_status"] = f"blocked: {e}"
        except Exception as e:
            row["fulltext_status"] = f"error: {type(e).__name__}: {str(e)[:120]}"
        if n % 50 == 0:
            table.save()
            print(f"{n}/{len(rows)} {row['id']} {row['fulltext_status']}", flush=True)
    table.save()


def main() -> None:
    p = Polite(SOURCE, base_delay=0.25, host_min={"www.ebi.ac.uk": 10})
    table = MetaTable(SOURCE)
    if "--fetch-only" not in sys.argv:
        search(p, table)
    if "--search-only" not in sys.argv:
        fetch_all(p, table)
    print("bytes", folder_bytes(SOURCE))


if __name__ == "__main__":
    main()
