"""Early modern English dream books and treatises from EEBO-TCP / Evans-TCP / ECCO-TCP (CC0 transcriptions).

Selected from the TCP catalogue (TCP.csv, status "Free") by title/subject "dream". Restricted TCP texts are
not fetched. Entries: sentence-level sign -> meaning pairs from the dream-list chapters of Thomas Hill,
"The moste pleasuante arte of the interpretacion of dreames" (1576), whose last part is a
Somniale-Danielis-type list ("gathered out of the Pamphlettes of the wyse Salomon, holye Joseph, and Daniell"),
and from any chapter whose heading names dreams in Erra Pater's Book of Knowledge (1796).

Run: backend/.venv/Scripts/python -m corpus.sources.eebo_dreambooks
"""

from __future__ import annotations

import re

from corpus.fetch import Fetcher, Meta, write_entries
from corpus.sources.greco_common import get_or_load, reset_entries, row, sentences, tei_clean

SOURCE = "eebo-dreambooks"
TRADITION = "avrupa-erken-modern"
LICENSE = "CC0 1.0 (Text Creation Partnership transcription of a public-domain imprint)"
RIGHTS = "Text Creation Partnership (Univ. of Michigan / Bodleian, Oxford); contact tcp-info@umich.edu"

TEXTS = {
    "A03378": ("Hill, Thomas", "The moste pleasuante arte of the interpretacion of dreames, 1576",
               r"^(Of those Dreames|Certain briefe Dreames)"),
    "A63809": ("Tryon, Thomas", "Pythagoras his mystick philosophy reviv'd, or, The mystery of dreams unfolded, 1691", None),
    "A63812": ("Tryon, Thomas", "A treatise of dreams & visions, 1689", None),
    "A81567": ("Gonzalo", "The divine dreamer: or, a short treatise discovering the true effect and power of dreames, 1641", None),
    "A85424": ("Goodwin, Philip", "The mystery of dreames, historically discoursed, 1658", None),
    "A25315": ("Amyraut, Moise", "A discourse concerning the divine dreams mention'd in Scripture, 1676", None),
    "N23008": ("Erra Pater (tr. W. Lilly)", "The book of knowledge: treating of the wisdom of the ancients, 1796", r"dream"),
    "K046060.000": ("More, Hannah", "Tawny Rachel, or, the fortune teller; with some account of dreams, omens and conjurers, 1796", None),
    "N17980": ("Conover, Samuel Forman", "An inaugural dissertation on sleep and dreams, 1791", None),
}

VERB = re.compile(r"\b(signif\w*|sygnif\w*|declar\w*|betoken\w*|shew\w*|denot\w*|portend\w*|foreshew\w*|argu\w*|"
                  r"pronosticat\w*|is a sign|it is a sign|import\w*)\b|,\s*(?:that|then)\s+(?:he|she|they|the)\b", re.I)


NARRATIVE = re.compile(r"^(Which|Whiche|For|This|That|It|They|He|She|Whereof|Wherefore|But|And this|So)\b")


def chunks(xml: str):
    """(head, text) chunks: a heading and everything until the next heading."""
    parts = re.split(r"(?=<head[ >])", xml)
    for p in parts[1:]:
        hm = re.match(r"<head[^>]*>(.*?)</head>", p, re.S)
        if not hm:
            continue
        yield tei_clean(hm.group(1)), tei_clean(p[hm.end():])


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition=TRADITION))
    reset_entries(SOURCE)
    rows = []
    for tcp_id, (author, title, pat) in TEXTS.items():
        url = f"https://raw.githubusercontent.com/textcreationpartnership/{tcp_id}/master/{tcp_id}.xml"
        body = get_or_load(f, url, name=f"{tcp_id}.xml")
        if not body or not pat:
            continue
        xml = body.decode("utf-8", "replace")
        for head, text in chunks(xml):
            if not re.search(pat, head, re.I):
                continue
            for i, s in enumerate(sentences(text), 1):
                m = VERB.search(s)
                if not m or m.start() < 8 or not re.search(r"dream|dreme|seem|seme|see", s[:m.start() + 40], re.I) and tcp_id != "A03378":
                    continue
                if not m or m.start() < 8:
                    continue
                lead = s[:m.start()]
                if NARRATIVE.match(lead) and not re.search(r"dream|dreme|seem|seme|\bsee?\b", lead, re.I):
                    continue
                rows.append(row(source=SOURCE, tradition=TRADITION, language="en",
                                symbol_raw=s[:m.start()].strip(" ,;:"), meaning=s, url=url,
                                locator=f"{tcp_id}, chapter '{head[:60]}', sentence {i}",
                                license=LICENSE, rights_holder=RIGHTS, attributed_author=author, edition=title))
    path = write_entries(SOURCE, rows)
    print("wrote", len(rows), "->", path)


if __name__ == "__main__":
    main()
