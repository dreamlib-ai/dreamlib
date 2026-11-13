"""Artemidorus, Oneirocritica.

- 1644 English translation (R.W.), EEBO-TCP A25906, CC0  -> one entry per chapter (head = symbol)
- 1659 Welsh abridgement, EEBO-TCP A75627, CC0            -> one entry per chapter
- Greek text, First1KGreek tlg0553.tlg001 (CC BY-SA 4.0; digitised from Pack 1963) -> one entry per chapter
- Reiff 1805 Greek/Latin (archive.org, PD) and Krauss 1881 German (BIU Sante, Etalab open licence): raw scans + OCR

The archive.org item `Artemidorus` (2016 "Teubner" scan, likely Pack 1963) is deliberately not fetched.

Run: backend/.venv/Scripts/python -m corpus.sources.artemidorus
"""

from __future__ import annotations

import re

from corpus.fetch import Fetcher, Meta, write_entries
from corpus.sources.greco_common import get_or_load, reset_entries, row, tei_sections

SOURCE = "artemidorus"
TRADITION = "greko-romen"

TCP = {
    "A25906": {
        "lang": "en",
        "license": "CC0 1.0 (EEBO-TCP Phase I transcription; 1644 work public domain)",
        "edition": "The interpretation of dreams digested into five books, London: Bernard Alsop 1644, tr. R.W.",
    },
    "A75627": {
        "lang": "cy",
        "license": "CC0 1.0 (EEBO-TCP transcription; 1659 work public domain)",
        "edition": "Gwir ddeongliad breuddwydion (Welsh abridgement of Artemidorus), 1659",
    },
}
TCP_RIGHTS = "Text Creation Partnership (Univ. of Michigan / Bodleian, Oxford); contact tcp-info@umich.edu"

GRC_URL = ("https://raw.githubusercontent.com/OpenGreekAndLatin/First1KGreek/master/"
           "data/tlg0553/tlg001/tlg0553.tlg001.1st1K-grc1.xml")
GRC_CTS = "https://raw.githubusercontent.com/OpenGreekAndLatin/First1KGreek/master/data/tlg0553/tlg001/__cts__.xml"
GRC_LICENSE = "CC BY-SA 4.0 (First1KGreek digital text; base edition Pack, Teubner 1963)"
GRC_RIGHTS = "Harvard College Library / Open Greek and Latin (First1KGreek), Univ. of Leipzig; github.com/OpenGreekAndLatin/First1KGreek"

ARCHIVE = [
    # (identifier, files, license, rights)
    ("oneirocritica01arte", ["oneirocritica01arte_djvu.txt", "oneirocritica01arte.pdf"],
     "public domain (Reiff ed. 1805)", "Internet Archive scan, University of Toronto Robarts Library"),
    ("oneirocriticaex00rigagoog", ["oneirocriticaex00rigagoog_djvu.txt"],
     "public domain (Reiff ed. 1805, vol. 2 / notes)", "Internet Archive (Google scan, Harvard University)"),
    ("BIUSante_55615", ["BIUSante_55615_djvu.txt", "BIUSante_55615.pdf"],
     "public domain work; scan under Licence Ouverte / Etalab", "BIU Sante (Universite Paris Cite), via Internet Archive"),
]


def tcp(f: Fetcher, tcp_id: str) -> list[dict]:
    cfg = TCP[tcp_id]
    url = f"https://raw.githubusercontent.com/textcreationpartnership/{tcp_id}/master/{tcp_id}.xml"
    body = get_or_load(f, url, name=f"{tcp_id}.xml")
    if body is None:
        return []
    xml = body.decode("utf-8")
    out = []
    epitome = False
    for s in tei_sections(xml):
        if not s["head"] and not s["body"]:
            continue
        book = s["book"]
        head = s["head"]
        # Book V of the 1644 text is one chapter of example dreams: one entry per reported dream
        if tcp_id == "A25906" and head.startswith("Containing certain examples"):
            n = 0
            for i, p in enumerate(s["paras"], 1):
                for ex in EXAMPLE_SPLIT.split(p):
                    if not ex.strip():
                        continue
                    n += 1
                    out.append(row(source=SOURCE, tradition=TRADITION, language=cfg["lang"], symbol_raw="",
                                   meaning=ex.strip(), url=url, locator=f"{tcp_id} book {book}, examples ¶{i}, dream {n}",
                                   license=cfg["license"], rights_holder=TCP_RIGHTS,
                                   attributed_author="Artemidorus Daldianus", edition=cfg["edition"],
                                   entry_type="example_dream"))
            epitome = True  # what follows in book V is the translator's epitome of Valerius Maximus
            continue
        etype, author = "chapter", "Artemidorus Daldianus"
        if epitome:
            etype, author = "valerius_maximus_epitome", "Valerius Maximus (epitome added by the 1644 translator)"
        elif re.search(r"Translatour|Preface|Conclusion|TO HIS|TRANSLATOVR", head):
            etype = "frame_text"
        out.append(row(source=SOURCE, tradition=TRADITION, language=cfg["lang"], symbol_raw=head if etype == "chapter" else "",
                       meaning=s["body"], url=url,
                       locator=f"{tcp_id} book {book or '-'}, chapter {s['idx']}",
                       license=cfg["license"], rights_holder=TCP_RIGHTS,
                       attributed_author=author, edition=cfg["edition"],
                       entry_type=etype, head=head))
    return out


EXAMPLE_SPLIT = re.compile(r"(?<=[.:;])\s+(?=(?:A|An|Another|One|Some|A certaine?)\b[^.]{0,40}?\bdre[a]?m)")


def grc_clean(frag: str) -> str:
    s = re.sub(r"<note[^>]*>.*?</note>", " ", frag, flags=re.S)
    s = re.sub(r"<del[^>]*>.*?</del>", " ", s, flags=re.S)
    s = re.sub(r"<gap[^>]*/>", " … ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def greek(f: Fetcher) -> list[dict]:
    get_or_load(f, GRC_CTS, name="tlg0553.tlg001__cts__.xml")
    body = get_or_load(f, GRC_URL, name="tlg0553.tlg001.1st1K-grc1.xml")
    if body is None:
        return []
    xml = body.decode("utf-8")
    out = []
    books = re.split(r'<div type="textpart" subtype="book" n="', xml)[1:]
    for b in books:
        bn = b.split('"', 1)[0]
        for m in re.finditer(r'<div type="textpart" subtype="section" n="([^"]+)">(.*?)(?=<div type="textpart"|</body>|\Z)', b, re.S):
            sec, frag = m.group(1), m.group(2)
            hm = re.search(r"<head[^>]*>(.*?)</head>", frag, re.S)
            text = grc_clean(frag)
            if not text:
                continue
            out.append(row(source=SOURCE, tradition=TRADITION, language="grc",
                           symbol_raw="", meaning=text, url=GRC_URL,
                           locator=f"urn:cts:greekLit:tlg0553.tlg001.1st1K-grc1:{bn}.{sec}",
                           license=GRC_LICENSE, rights_holder=GRC_RIGHTS,
                           attributed_author="Artemidorus Daldianus",
                           edition="Artemidori Daldiani Onirocriticon, ed. R. A. Pack, Teubner 1963 (First1KGreek TEI)",
                           entry_type="chapter", head=grc_clean(hm.group(1)) if hm else ""))
    return out


def archive(f: Fetcher) -> None:
    for ident, files, lic, rights in ARCHIVE:
        f.meta.license, f.meta.rights_holder = lic, rights
        get_or_load(f, f"https://archive.org/metadata/{ident}", name=f"{ident}_metadata.json")
        for fn in files:
            get_or_load(f, f"https://archive.org/download/{ident}/{fn}", name=fn)


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, license=TCP["A25906"]["license"], rights_holder=TCP_RIGHTS, tradition=TRADITION))
    reset_entries(SOURCE)
    rows = []
    for tcp_id in TCP:
        f.meta.license = TCP[tcp_id]["license"]
        f.meta.rights_holder = TCP_RIGHTS
        part = tcp(f, tcp_id)
        print(tcp_id, len(part), "entries")
        rows += part
    f.meta.license, f.meta.rights_holder = GRC_LICENSE, GRC_RIGHTS
    part = greek(f)
    print("grc", len(part), "entries")
    rows += part
    archive(f)
    path = write_entries(SOURCE, rows)
    print("wrote", len(rows), "->", path)


if __name__ == "__main__":
    main()
