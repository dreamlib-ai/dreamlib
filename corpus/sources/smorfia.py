"""La Smorfia Napoletana (dream symbol -> lotto numbers 1-90).

Sources (one raw folder each):
  smorfia-it-wikipedia-org     it.wikipedia "Smorfia napoletana" alphabetical list (CC BY-SA 4.0)
  smorfia-sognipedia-it        sognipedia.it dream pages ("Sognare X: ..." + Numeri section)
  smorfia-librodeisogni-net    librodeisogni.net dream posts (article + cabala/smorfia numbers)

Run: backend/.venv/Scripts/python -m corpus.sources.smorfia [source ...] [--fetch-only]
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from corpus.sources.dreamnum_common import Site, blocks, body_text, clean, h1, main, region, split_conditions

TRAD = "smorfia-napoletana"
NUM = r"(?<!\d)(?:[1-9]|[1-8]\d|90)(?!\d)"


def nums(s: str) -> list[int]:
    return [int(x) for x in re.findall(NUM, s)]


# ------------------------------------------------------------ wikipedia

class _WikiList(HTMLParser):
    """Collect nested <li> items under single-letter h2 sections."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = ""
        self.in_h2 = False
        self.h2buf = ""
        self.items: list[tuple[str, int, str]] = []  # (section, depth, text)
        self.stack: list[list[str] | None] = []
        self.skip = 0

    def _emit(self, parts):
        txt = clean("".join(parts))
        if txt and len(self.section) == 1:
            self.items.append((self.section, len(self.stack), txt))

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "sup"):
            self.skip += 1
        if tag == "h2":
            self.in_h2, self.h2buf = True, ""
        elif tag == "ul" and self.stack and self.stack[-1] is not None:
            self._emit(self.stack[-1])
            self.stack[-1] = None
        elif tag == "li":
            self.stack.append([])

    def handle_endtag(self, tag):
        if tag in ("style", "script", "sup"):
            self.skip = max(0, self.skip - 1)
        if tag == "h2":
            self.in_h2 = False
            self.section = clean(self.h2buf)
        elif tag == "li" and self.stack:
            top = self.stack[-1]
            if top is not None:
                self._emit(top)
            self.stack.pop()

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_h2:
            self.h2buf += data
        elif self.stack and self.stack[-1] is not None:
            self.stack[-1].append(data)


def parse_wiki(url: str, html: str) -> list[dict]:
    p = _WikiList()
    p.feed(html)
    rows, parent = [], ""
    for section, depth, line in p.items:
        m = re.match(r"(.+?)\s+((?:\d{1,2}\s*[,;/\-–]\s*)*\d{1,2})\s*$", line)
        label, numtxt = (m.group(1), m.group(2)) if m else (line, "")
        if depth == 1:
            parent = label
            symbol, cond = label, ""
        else:
            symbol, cond = parent, label
        n = nums(numtxt)
        if not n:
            continue
        rows.append({"symbol_raw": symbol, "condition": cond, "meaning": "", "numbers": n,
                     "locator": f"sezione {section}", "url": url})
    return rows


# ------------------------------------------------------------ sognipedia

def parse_sognipedia(url: str, html: str) -> list[dict]:
    title = h1(html)
    sym = re.sub(r"(?i)^sogn(are|i)\s+", "", title)
    sym = re.split(r"\s+[–\-|]\s+", sym)[0].strip()
    art = region(html, [r'<div[^>]+class="[^"]*entry-content', r"<article", r"<h1"],
                 [r'class="[^"]*(sharedaddy|jp-relatedposts|comments-area|yarpp)', r'id="comments"', r"<footer"])
    bl = blocks(art or html)
    rows = []
    stop = r"^(Note Editoriali|Commenti|Lascia un commento)"
    intro = body_text(bl, stop_re=r"^(Numeri|Note Editoriali)$|Se continui la lettura", limit=1500)
    numbers_txt = ""
    take = False
    for tag, t, lead in bl:
        if re.match(r"^Numeri\b", t):
            take = True
            if len(t) > 10:
                numbers_txt += " " + t
            continue
        if take:
            if re.search(stop, t) or tag.startswith("h"):
                break
            numbers_txt += " " + t
    if intro:
        rows.append({"symbol_raw": sym, "condition": "", "meaning": intro, "locator": "intro"})
    for cond, mean in split_conditions(bl, r"Sognare|Sognar|Sogno|Vedere|Essere"):
        rows.append({"symbol_raw": sym, "condition": cond, "meaning": mean, "locator": "significato"})
    # numbers: "... è il numero 7 ; esserne sporco di fango 39 ."
    numbers_txt = re.sub(r"\s+", " ", numbers_txt).strip()
    if numbers_txt:
        parts = re.split(r"\s*;\s*", numbers_txt)
        for i, p in enumerate(parts):
            n = nums(p)
            if not n:
                continue
            cond = "" if i == 0 else re.sub(r"[\d\s,.]+$", "", p).strip()
            rows.append({"symbol_raw": sym, "condition": cond, "meaning": p.strip(), "numbers": n,
                         "locator": "Numeri"})
    return rows


# ------------------------------------------------------------ librodeisogni

def parse_librodeisogni(url: str, html: str) -> list[dict]:
    title = h1(html)
    sym = re.sub(r"(?i)^sognare\s+(di\s+)?", "", title)
    sym = re.split(r"\s+[–\-|:]\s+", sym)[0].strip()
    art = region(html, [r'<div[^>]+class="[^"]*entry-content', r"<article"],
                 [r'id="comments"', r'class="[^"]*(comments-area|yarpp|related)', r"Sogni collegati"])
    bl = blocks(art or html)
    rows = []
    body = []
    num_mode = False
    numbers: list[int] = []
    num_lines = []
    for tag, t, lead in bl:
        if re.search(r"(?i)numer[io].{0,40}(cabala|smorfia|giocare|lotto)|(cabala|smorfia).{0,40}numer", t) and tag.startswith("h"):
            num_mode = True
            continue
        if num_mode:
            if tag.startswith("h") and not re.search(r"(?i)numer", t):
                num_mode = False
            else:
                m = re.match(r"^\s*(\d{1,2})\s*[:\-–.)]\s*(.+)", t)
                if m and 1 <= int(m.group(1)) <= 90:
                    numbers.append(int(m.group(1)))
                    num_lines.append(t)
                    rows.append({"symbol_raw": sym, "condition": "", "meaning": t, "numbers": [int(m.group(1))],
                                 "locator": "numeri della cabala"})
                    continue
                # inline "numeri: 12, 45, 78"
                n = nums(t) if re.search(r"(?i)numer", t) else []
                if n and len(t) < 300:
                    rows.append({"symbol_raw": sym, "condition": "", "meaning": t, "numbers": n,
                                 "locator": "numeri della cabala"})
                continue
        if tag == "h1" or len(t) < 25:
            continue
        body.append(t)
    if body:
        rows.insert(0, {"symbol_raw": sym, "condition": "", "meaning": "\n".join(body)[:8000],
                        "locator": "articolo", "attributed_author": "Marisa (librodeisogni.net)"})
    return rows


SITES = {
    "smorfia-it-wikipedia-org": Site(
        source="smorfia-it-wikipedia-org", tradition=TRAD, language="it",
        license="CC BY-SA 4.0", rights_holder="Wikipedia contributors (Wikimedia Foundation)",
        delay=2.0, extra_urls=["https://it.wikipedia.org/wiki/La_smorfia_napoletana"], parse=parse_wiki),
    "smorfia-sognipedia-it": Site(
        source="smorfia-sognipedia-it", tradition=TRAD, language="it",
        rights_holder="Sognipedia.it (operator per site imprint)",
        delay=2.0, sitemaps=["https://www.sognipedia.it/sitemap.xml.gz"],
        sitemap_child_re=r"sitemap-pt-post", url_re=r"sognipedia\.it/sogn[^/]*/?$", parse=parse_sognipedia),
    "smorfia-librodeisogni-net": Site(
        source="smorfia-librodeisogni-net", tradition=TRAD, language="it",
        rights_holder="librodeisogni.net (Marisa, astrologa, Caserta)",
        delay=2.0, sitemaps=["https://www.librodeisogni.net/sitemap_index.xml"],
        sitemap_child_re=r"post-sitemap", url_re=r"librodeisogni\.net/[^/]+/$", parse=parse_librodeisogni),
}

if __name__ == "__main__":
    main(SITES)
