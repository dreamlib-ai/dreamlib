"""French clé des songes / dictionnaire des rêves.

  reves-interpretation-reve-fr   interpretation-reve.fr  (~4000 entries; numbered interpretations,
                                 Miller / Nostradamus / Artémidore blocks, "chiffres de chance")
  reves-signification-reve-fr    signification-reve.fr   (~3600 entries; "Interprétation du rêve n° N")

Run: backend/.venv/Scripts/python -m corpus.sources.reves [source ...] [--fetch-only]
"""

from __future__ import annotations

import re

from corpus.sources.dreamnum_common import Site, author_in, blocks, clean, h1, main, region, sections

TRAD = "clé des songes (fr)"


def _sym_from_url(url: str) -> str:
    s = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.(htm|php)l?$", "", s).replace("-", " ")


def parse_interpretation_reve(url: str, html: str) -> list[dict]:
    title = h1(html)
    sym = re.sub(r"(?i)^.*?r[êe]ve\s*:\s*", "", title).strip() or _sym_from_url(url)
    islam = "-islam" in url
    art = region(html, [r"<h1"], [r"Les visiteurs qui ont consult", r'class="TopFooter'])
    rows = []
    for head, txt in sections(blocks(art), heads=("h2",)):
        hl = head.lower()
        if not head or "rêves associés" in hl or "reves associes" in hl:
            continue
        if re.search(r"chiffres? de chance", hl):
            n = [int(x) for x in re.findall(r"\d{1,3}", txt)]
            if n:
                rows.append({"symbol_raw": sym, "condition": "", "meaning": txt, "numbers": n,
                             "locator": head})
            continue
        if len(txt) < 20:
            continue
        rows.append({"symbol_raw": sym, "condition": "islam" if islam else "", "meaning": txt,
                     "locator": head.rstrip(" :"), "attributed_author": author_in(head)})
    return rows


def parse_signification_reve(url: str, html: str) -> list[dict]:
    title = h1(html)
    m = re.search(r"(?i)r\S{1,2}ver\s+(?:de\s+|d'|du\s+|des\s+)(.+)$", title)
    sym = m.group(1).strip() if m else _sym_from_url(url)
    art = region(html, [r"<h1"], [r"Interpr[^<]{0,12}tation des r[^<]{0,6}ves gratuite", r"Publi[^<]{0,4} par"])
    txt = "\n".join(t for _, t, _ in blocks(art) if t)
    author = clean(re.search(r"Publi\S* par\s*([^<\n]{2,40})", html).group(1)) if re.search(r"Publi\S* par\s*([^<\n]{2,40})", html) else ""
    parts = re.split(r"(Interpr\S*tation du r\S*ve n\S*\s*\d+[^:]{0,80}:)", txt)
    rows = []
    for i in range(1, len(parts) - 1, 2):
        head, body = parts[i].strip(" :"), parts[i + 1].strip()
        if len(body) > 20:
            rows.append({"symbol_raw": sym, "condition": "", "meaning": body, "locator": head,
                         "attributed_author": author})
    if not rows and len(txt) > 80:
        rows.append({"symbol_raw": sym, "condition": "", "meaning": txt, "locator": "", "attributed_author": author})
    return rows


SITES = {
    "reves-interpretation-reve-fr": Site(
        source="reves-interpretation-reve-fr", tradition=TRAD, language="fr",
        rights_holder="interpretation-reve.fr (operator per mentions légales)",
        delay=2.0, sitemaps=["https://interpretation-reve.fr/sitemap.xml"],
        url_re=r"/dictionnaire-reve-[A-Z]/[^/?]+\.htm$", parse=parse_interpretation_reve),
    "reves-signification-reve-fr": Site(
        source="reves-signification-reve-fr", tradition=TRAD, language="fr",
        rights_holder="signification-reve.fr (operator per mentions légales)",
        delay=2.0, sitemaps=["https://signification-reve.fr/sitemap.xml"],
        url_re=r"/interpretation-reve-lettre-[a-z]/[^/?]+\.php$", parse=parse_signification_reve),
}

if __name__ == "__main__":
    main(SITES)
