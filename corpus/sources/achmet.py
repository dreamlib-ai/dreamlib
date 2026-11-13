"""Achmet, Oneirocriticon (Byzantine, c. 9th-10th c.) and companions.

- Rigault 1603 edition (Artemidorus + Achmet + Astrampsychos + Nikephoros), two archive.org scans:
  Duke (artemidoridaldia00arte) and BIU Sante (BIUSante_07767, Etalab open licence). The Achmet part
  prints the Greek with a facing Latin version; the Latin OCR is usable, the Greek OCR is not.
  -> one entry per Latin "Si quis ... viderit" paragraph, grouped under the chapter heading.
- Drexl 1909, Achmets Traumbuch. Einleitung und Probe eines kritischen Textes (Leiden thesis scan).
- Mavroudi 2002 (Brill, CC BY 4.0): OAPEN host refuses bots (403); the OAPEN mirror on archive.org is used.
- Opsopoeus 1599, Oracula metrica (contains Astrampsychos' dream verses), PD mark.

Run: backend/.venv/Scripts/python -m corpus.sources.achmet
"""

from __future__ import annotations

import re

from corpus.fetch import Fetcher, Meta, write_entries
from corpus.sources.greco_common import get_or_load, reset_entries, row, try_get

SOURCE = "achmet"
TRADITION = "bizans"

ITEMS = [
    # identifier, files, license, rights holder
    ("artemidoridaldia00arte", ["artemidoridaldia00arte_djvu.txt", "artemidoridaldia00arte.pdf"],
     "public domain (Rigault ed., Paris 1603)", "Internet Archive scan, Duke University Libraries (Rubenstein)"),
    ("BIUSante_07767", ["BIUSante_07767_djvu.txt", "BIUSante_07767.pdf"],
     "public domain work; scan under Licence Ouverte / Etalab", "BIU Sante (Universite Paris Cite), via Internet Archive"),
    ("IA41548314_0078", ["IA41548314_0078_djvu.txt", "IA41548314_0078.pdf"],
     "public domain in the US (published 1909); EU status depends on F. X. Drexl's death date",
     "Internet Archive scan, Leiden University Libraries (theses collection)"),
    ("oapen-20.500.12657-54647", ["9789004473461_djvu.txt", "9789004473461.pdf"],
     "CC BY 4.0 (Mavroudi 2002, Brill open access; third-party quotations may need separate permission)",
     "Koninklijke Brill NV / author Maria Mavroudi; OA via OAPEN (library.oapen.org)"),
    ("bub_gb_bw86f-Vs53QC", ["bub_gb_bw86f-Vs53QC_djvu.txt", "bub_gb_bw86f-Vs53QC.pdf"],
     "Public Domain Mark 1.0 (Opsopoeus, Oracula metrica, Paris 1599)", "Internet Archive (Google Books scan, European library)"),
]
OAPEN_TRIES = [
    "https://library.oapen.org/bitstream/20.500.12657/54647/1/9789004473461.pdf",
    "https://directory.doabooks.org/handle/20.500.12854/81797",
    "https://brill.com/display/title/61697",
]

DUKE_TXT = "https://archive.org/download/artemidoridaldia00arte/artemidoridaldia00arte_djvu.txt"

LAT = set("""quis fuerit vifus visus videre viderit fignificat significat erit et in ex fibi sibi fi si ac eft est
non quod vel cum ad aut fe se fuo suo eius eum qui quae fed sed hoc ille illi autem enim ipfe ipse eo ea
fomnis somnis fomniis somniis fuerint habebit inueniet adfequetur confequetur""".split())
CAP = re.compile(r"\b(?:C\s?[A-Z]\s?[A-Z]|CAP|C\s?A\s?P|CIAS|CP)[\s.,:;]*([0-9IlOoSG]{1,4})\s*[.,:]")
START = re.compile(r"^\W{0,3}(S\s?I\b|Si\b|Si[a-z]|S\s?i\s|I\s?quis|Iquis|Sin\b|Quod\b|Qui\b|Quicun|Quod\s?si)")


def latin_score(p: str) -> float:
    toks = re.findall(r"[a-zA-Zæœ]+", p.lower())
    if len(toks) < 6:
        return 0.0
    return sum(t in LAT for t in toks) / len(toks)


def clean(s: str) -> str:
    s = s.replace("|", " ")
    s = re.sub(r"-\s*\n\s*", "", s)  # OCR line-end hyphenation
    return re.sub(r"\s+", " ", s).strip(" .,;:'\"«»")


def parse_latin(text: str) -> list[dict]:
    m = re.search(r"Ex\s+IN\s?D\s?OR\w*\s+DISCIPLINA", text)
    if not m:
        return []
    region = text[m.start():]
    blocks = [b for b in re.split(r"\n\s*\n", region) if b.strip()]
    out, head, cap_ocr, chap = [], "", "", 0
    for b in blocks:
        one = clean(b)
        cm = CAP.search(one)
        if cm and len(one) < 160:
            pre = one[:cm.start()].strip(" .,;:")
            if pre:
                head = pre
            cap_ocr = cm.group(1)
            chap += 1
            continue
        if re.match(r"^(De|Ex)\s", one) and len(one) < 120 and latin_score(one) < 0.6:
            head = one
            continue
        if latin_score(one) >= 0.18 and START.match(one):
            out.append({"chapter_seq": chap, "cap_ocr": cap_ocr, "head": head, "text": one})
    return out


def symbol_from_head(head: str) -> str:
    h = re.sub(r",?\s*(ex|ab)\s+\w*\s*(Indorum|Perfarum|Persarum|Aegyptiorum|Aegyptior|egyptior)\b.*$", "", head, flags=re.I)
    h = re.sub(r"^(Ex\s+\w+\s+\w+\s*,?\s*)", "", h)  # "Ex disciplina Indorum, de Barba"
    return h.strip(" ,.;:")


def condition_meaning(p: str) -> tuple[str, str]:
    """Split 'Si quis ... viderit : meaning' at the first colon (typical of this Latin version)."""
    i = p.find(":")
    if 15 < i < 400:
        return p[:i].strip(), p
    return "", p


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, tradition=TRADITION))
    reset_entries(SOURCE)
    for ident, files, lic, rights in ITEMS:
        f.meta.license, f.meta.rights_holder = lic, rights
        get_or_load(f, f"https://archive.org/metadata/{ident}", name=f"{ident}_metadata.json")
        for fn in files:
            get_or_load(f, f"https://archive.org/download/{ident}/{fn}", name=fn)
    f.meta.license, f.meta.rights_holder = ITEMS[3][2], ITEMS[3][3]
    for u in OAPEN_TRIES:
        if not f.seen(u):
            try_get(f, u)

    body = get_or_load(f, DUKE_TXT)
    rows = []
    if body:
        paras = parse_latin(body.decode("utf-8", "replace"))
        for i, p in enumerate(paras, 1):
            cond, meaning = condition_meaning(p["text"])
            rows.append(row(
                source=SOURCE, tradition=TRADITION, language="la",
                symbol_raw=symbol_from_head(p["head"]), condition=cond, meaning=meaning,
                url="https://archive.org/details/artemidoridaldia00arte",
                locator=f"Achmet (Latin), chapter seq {p['chapter_seq']} (OCR 'CAP. {p['cap_ocr']}'), para {i}",
                license=ITEMS[0][2], rights_holder=ITEMS[0][3],
                attributed_author="Achmet son of Seirim (Ps.-Achmet)",
                edition="Achmetis F. Seirim Oneirocritica, in N. Rigault (ed.), Artemidori Daldiani & Achmetis Sereimi f. Oneirocritica, Paris 1603 (Latin version)",
                chapter_head_raw=p["head"], text_basis="archive.org djvu OCR, uncorrected (long s read as f)",
            ))
    path = write_entries(SOURCE, rows)
    print("wrote", len(rows), "->", path)


if __name__ == "__main__":
    main()
