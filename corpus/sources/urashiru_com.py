"""ウラシル urashiru.com 夢占い辞典 (Japanese, modern, small commercial dictionary).

robots.txt: Allow all. /dream/<category>/ pages list keywords (anchors); each keyword has
/dream/<category>/<slug>/ with a 夢の意味・解釈 paragraph, an アドバイス paragraph and a
badge (吉/注意/普通...). Run: backend/.venv/Scripts/python -m corpus.sources.urashiru_com
"""
from __future__ import annotations

import html
import re

from corpus.fetch import Fetcher, Meta
from corpus.sources.krjp_common import get_text, run

SOURCE = "urashiru.com"
SITE = "https://urashiru.com"
LICENSE = "All rights reserved (no open license stated)"
RIGHTS = "ウラシル urashiru.com (operator per site 'ウラシルについて' /about/)"
POL = {"吉": "iyi", "大吉": "iyi", "良い": "iyi", "注意": "kötü", "凶": "kötü", "普通": "nötr"}


def txt(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()


def parse(page: str, url: str) -> list[dict]:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    mean = re.search(r"夢の意味・解釈</span>.*?<div class=\"text-\[14px\][^>]*>(.*?)</div>", page, re.S)
    if not h1 or not mean:
        return []
    word = txt(h1.group(1))
    badge = re.search(r"</h1>\s*<div[^>]*>\s*<span[^>]*></span>\s*([^<]+)<", page, re.S)
    pol = POL.get(txt(badge.group(1)), "bilinmiyor") if badge else "bilinmiyor"
    cat = re.search(r'href="/dream/(\w+)/"', page)
    base = {"source": SOURCE, "tradition": "Japonya modern (夢占い)", "language": "ja", "domain": cat.group(1) if cat else "",
            "url": url, "license": LICENSE, "rights_holder": RIGHTS, "attributed_author": "", "headword": word}
    rows = [{**base, "symbol_raw": word, "condition": "", "meaning": txt(mean.group(1)), "polarity": pol,
             "locator": f"{word} #meaning"}]
    adv = re.search(r"アドバイス</span>.*?<div class=\"text-\[14px\][^>]*>(.*?)</div>", page, re.S)
    if adv:
        rows.append({**base, "symbol_raw": word, "condition": "アドバイス", "meaning": txt(adv.group(1)),
                     "polarity": "bilinmiyor", "locator": f"{word} #advice"})
    return rows


def parse_cat(page: str, url: str) -> list[dict]:
    cat = re.search(r"/dream/(\w+)/", url)
    rows = []
    for aid, art in re.findall(r'<article id="(\w+)"(.*?)</article>', page, re.S):
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", art, re.S)
        ps = re.findall(r"<p class=\"text-\[1[23](?:\.5)?px\][^>]*>(.*?)</p>", art, re.S)
        if not h2 or not ps:
            continue
        word = re.sub(r"の夢$", "", txt(h2.group(1)))
        b = re.search(r"</h2>\s*<span[^>]*>([^<]+)<", art)
        pol = POL.get(txt(b.group(1)), "bilinmiyor") if b else "bilinmiyor"
        base = {"source": SOURCE, "tradition": "Japonya modern (夢占い)", "language": "ja",
                "domain": cat.group(1) if cat else "", "url": f"{url}#{aid}", "license": LICENSE,
                "rights_holder": RIGHTS, "attributed_author": "", "headword": word}
        rows.append({**base, "symbol_raw": word, "condition": "", "meaning": txt(ps[0]), "polarity": pol,
                     "locator": f"{word} #cat-{aid}"})
        if len(ps) > 1:
            rows.append({**base, "symbol_raw": word, "condition": "ここから読み取れること", "meaning": txt(ps[1]),
                         "polarity": "bilinmiyor", "locator": f"{word} #cat-{aid}-advice"})
    return rows


def main() -> None:
    f = Fetcher(Meta(SOURCE, LICENSE, RIGHTS, "Japonya modern"), delay=1.5)
    home = get_text(f, f"{SITE}/dream/") or ""
    cats = sorted(set(re.findall(r'href="(/dream/\w+/)"', home)))
    urls: list[str] = []
    for c in cats:
        page = get_text(f, SITE + c) or ""
        for slug in re.findall(r'href="' + re.escape(c) + r'#(\w+)"', page):
            u = f"{SITE}{c}{slug}/"
            if u not in urls:
                urls.append(u)
        for m in re.findall(r'href="(' + re.escape(c) + r'[\w-]+/)"', page):
            u = SITE + m
            if u not in urls:
                urls.append(u)
    print("categories", cats, "keyword urls", len(urls), flush=True)
    run(f, SOURCE, urls, parse, 12000)
    from corpus.fetch import write_entries
    for c in cats:
        write_entries(SOURCE, parse_cat(get_text(f, SITE + c) or "", SITE + c))
    print("category pages parsed", flush=True)


if __name__ == "__main__":
    main()
