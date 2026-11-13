"""Greco-Roman and early Christian theory of dreams (public-domain texts and translations).

Theory texts, not symbol dictionaries: stored raw (HTML / OCR text / scans). Entries are only written
where a text itself lists sign -> meaning pairs; Hippocratic Regimen IV (Littre's French, 1849) is
kept raw because the OCR needs manual chapter alignment first.

Run: backend/.venv/Scripts/python -m corpus.sources.classical_greco_roman
"""

from __future__ import annotations

import re

from corpus.fetch import Fetcher, Meta
from corpus.sources.greco_common import get_or_load, reset_entries, try_get

SOURCE = "classical-greco-roman"
TRADITION = "greko-romen"

HTML = [
    # url, name, license, rights holder
    ("https://classics.mit.edu/Aristotle/dreams.html", "aristotle_on_dreams_beare.html",
     "public domain translation (J. I. Beare, Oxford 1908); page layout (c) Internet Classics Archive",
     "Internet Classics Archive (Daniel C. Stevenson, Web Atomics)"),
    ("https://classics.mit.edu/Aristotle/prophesying.html", "aristotle_prophesying_by_dreams_beare.html",
     "public domain translation (J. I. Beare, Oxford 1908); page layout (c) Internet Classics Archive",
     "Internet Classics Archive (Daniel C. Stevenson, Web Atomics)"),
    ("https://classics.mit.edu/Aristotle/sleep.html", "aristotle_on_sleep_beare.html",
     "public domain translation (J. I. Beare, Oxford 1908); page layout (c) Internet Classics Archive",
     "Internet Classics Archive (Daniel C. Stevenson, Web Atomics)"),
    ("https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Cicero/de_Divinatione/1*.html", "cicero_de_divinatione_1_en_falconer.html",
     "public domain (W. A. Falconer, Loeb 1923; US PD)", "LacusCurtius, Bill Thayer (penelope.uchicago.edu)"),
    ("https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Cicero/de_Divinatione/2*.html", "cicero_de_divinatione_2_en_falconer.html",
     "public domain (W. A. Falconer, Loeb 1923; US PD)", "LacusCurtius, Bill Thayer (penelope.uchicago.edu)"),
    ("https://penelope.uchicago.edu/Thayer/L/Roman/Texts/Cicero/de_Divinatione/1*.html", "cicero_de_divinatione_1_la.html",
     "public domain (Latin text, Loeb 1923)", "LacusCurtius, Bill Thayer (penelope.uchicago.edu)"),
    ("https://penelope.uchicago.edu/Thayer/L/Roman/Texts/Cicero/de_Divinatione/2*.html", "cicero_de_divinatione_2_la.html",
     "public domain (Latin text, Loeb 1923)", "LacusCurtius, Bill Thayer (penelope.uchicago.edu)"),
    ("https://www.newadvent.org/fathers/0310.htm", "tertullian_de_anima_anf.html",
     "public domain translation (P. Holmes, ANF vol. 3, 1885); transcription New Advent (Kevin Knight)",
     "New Advent (newadvent.org, Kevin Knight)"),
    ("https://www.newadvent.org/fathers/2914.htm", "gregory_nyssa_making_of_man_npnf.html",
     "public domain translation (H. A. Wilson, NPNF II/5, 1893); transcription New Advent",
     "New Advent (newadvent.org, Kevin Knight)"),
    ("http://www.earlychristianwritings.com/yonge/book20.html", "philo_de_somniis_1_yonge.html",
     "public domain translation (C. D. Yonge, 1854-55)", "earlychristianwritings.com (Peter Kirby)"),
    ("http://www.earlychristianwritings.com/yonge/book21.html", "philo_de_somniis_2_yonge.html",
     "public domain translation (C. D. Yonge, 1854-55)", "earlychristianwritings.com (Peter Kirby)"),
]

SYNESIUS_INDEX = "https://www.livius.org/sources/content/synesius/synesius-dreams/"
SYNESIUS_LIC = ("translation A. Fitzgerald, Oxford UP 1930: public domain in the US since 2026-01-01 (95 years); "
                "UK/EU status depends on the translator's death date; page text (c) Livius.org")
SYNESIUS_RIGHTS = "Livius.org (Jona Lendering); Oxford University Press for the 1930 translation"

ARCHIVE = [
    ("BIUSante_34859x06", ["BIUSante_34859x06_djvu.txt", "BIUSante_34859x06.pdf"],
     "public domain work (Littre, Oeuvres completes d'Hippocrate vol. 6, 1849: Du regime IV / Des songes); scan under Licence Ouverte / Etalab",
     "BIU Sante (Universite Paris Cite), via Internet Archive"),
    ("macrobius00cicegoog", ["macrobius00cicegoog_djvu.txt"],
     "public domain (Macrobius, ed. F. Eyssenhardt, Teubner 1893: Commentarii in Somnium Scipionis + Saturnalia)",
     "Internet Archive (Google Books scan)"),
    ("10800793bsb", ["10800793bsb_djvu.txt"],
     "public domain (Synesii opera, ed. D. Petavius, reprint 1859 / Migne PG 66 incl. De insomniis)",
     "Bayerische Staatsbibliothek scan, via Internet Archive"),
]


def synesius(f: Fetcher) -> None:
    f.meta.license, f.meta.rights_holder = SYNESIUS_LIC, SYNESIUS_RIGHTS
    body = get_or_load(f, SYNESIUS_INDEX, name="synesius_dreams_index.html")
    if not body:
        return
    links = sorted(set(re.findall(r'href="(https://www\.livius\.org/sources/content/synesius/synesius-dreams/[^"#]+)"', body.decode("utf-8", "replace"))))
    for i, u in enumerate(links, 1):
        if u.rstrip("/") == SYNESIUS_INDEX.rstrip("/"):
            continue
        slug = u.rstrip("/").rsplit("/", 1)[-1]
        get_or_load(f, u, name=f"synesius_{slug}.html")


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, tradition=TRADITION))
    reset_entries(SOURCE)
    for url, name, lic, rights in HTML:
        f.meta.license, f.meta.rights_holder = lic, rights
        if not f.seen(url):
            try_get(f, url, name=name)
    synesius(f)
    for ident, files, lic, rights in ARCHIVE:
        f.meta.license, f.meta.rights_holder = lic, rights
        get_or_load(f, f"https://archive.org/metadata/{ident}", name=f"{ident}_metadata.json")
        for fn in files:
            get_or_load(f, f"https://archive.org/download/{ident}/{fn}", name=fn)
    print("done")


if __name__ == "__main__":
    main()
