"""몽신 mongsin.com 꿈 백과사전 (Korean, modern, programmatic/likely LLM-written pages).

robots.txt allows /dream/. Sitemap lists ~16k /dream/<slug> pages; we take a capped sample
(default 4000, in sitemap order) because the text looks machine-generated (low provenance).
Run: backend/.venv/Scripts/python -m corpus.sources.mongsin_com [cap]
"""
from __future__ import annotations

import html
import re
import sys

from corpus.fetch import Fetcher, Meta
from corpus.sources.krjp_common import run, sitemap_urls

SOURCE = "mongsin.com"
LICENSE = "All rights reserved (no open license stated; pages appear machine-generated)"
RIGHTS = "몽신 mongsin.com (operator not named on pages checked)"
POL = {"길몽": "iyi", "대길몽": "iyi", "흉몽": "kötü", "대흉": "kötü", "평몽": "nötr"}


def txt(x: str) -> str:
    x = re.sub(r"<br\s*/?>", "\n", x)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()


def parse(page: str, url: str) -> list[dict]:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if not h1:
        return []
    title = txt(h1.group(1))
    word = re.sub(r"\s*해몽$", "", title)
    cat = re.search(r'class="cat-badge">(.*?)<', page)
    grade = re.search(r'class="grade-pill[^"]*">(.*?)<', page)
    pol = POL.get(txt(grade.group(1)), "bilinmiyor") if grade else "bilinmiyor"
    base = {"source": SOURCE, "tradition": "Kore modern (çevrimiçi sözlük, makine üretimi izlenimi)", "language": "ko",
            "domain": txt(cat.group(1)) if cat else "", "url": url, "license": LICENSE, "rights_holder": RIGHTS,
            "attributed_author": "", "headword": word}
    rows = []
    gen = re.search(r"일반 해몽</h2>(.*?)</section>", page, re.S)
    if gen:
        ps = [txt(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", gen.group(1), re.S)]
        if ps:
            rows.append({**base, "symbol_raw": word, "condition": "", "meaning": ps[0], "polarity": pol,
                         "locator": f"{title} #general"})
    var = re.search(r"상황별 변형 해석</h2>(.*?)</section>", page, re.S)
    if var:
        for i, (lab, p) in enumerate(re.findall(r"<div[^>]*>([^<]{4,200})</div>\s*<p[^>]*>(.*?)</p>", var.group(1), re.S), 1):
            rows.append({**base, "symbol_raw": word, "condition": txt(lab), "meaning": txt(p), "polarity": "bilinmiyor",
                         "locator": f"{title} #var{i}"})
    return rows


def main() -> None:
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    f = Fetcher(Meta(SOURCE, LICENSE, RIGHTS, "Kore modern"), delay=1.2)
    urls = [u for u in sitemap_urls(f, "https://mongsin.com/sitemap.xml") if "/dream/" in u]
    print("urls", len(urls), flush=True)
    run(f, SOURCE, urls, parse, cap)


if __name__ == "__main__":
    main()
