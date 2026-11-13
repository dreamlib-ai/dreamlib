"""척척사주 sajuplus.com 꿈해몽 사전 (Korean; accordion of 'dream scene -> meaning' rows per keyword).

robots.txt: Allow all. Keyword pages come from /dream-interpretation-keywords and the sitemap.
Run: backend/.venv/Scripts/python -m corpus.sources.sajuplus_com
"""
from __future__ import annotations

import html
import re

from corpus.fetch import Fetcher, Meta
from corpus.sources.krjp_common import get_text, run, sitemap_urls

SOURCE = "sajuplus.com"
SITE = "https://sajuplus.com"
LICENSE = "All rights reserved (no open license stated)"
RIGHTS = "척척사주 sajuplus.com (operator not named on pages checked)"


def txt(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def pol(m: str) -> str:
    if re.search(r"길몽|횡재|성공|번창|좋은|행운|재물이 (?:들어|생)", m):
        return "iyi"
    if re.search(r"흉몽|불길|손해|실패|구설|근심|질병|다툼", m):
        return "kötü"
    return "bilinmiyor"


def parse(page: str, url: str) -> list[dict]:
    head = re.search(r'<div class="alert alert-light border mt-4">\s*<h3[^>]*>(.*?)</h3>(.*?)</div>', page, re.S)
    if not head:
        return []
    word = txt(head.group(1))
    base = {"source": SOURCE, "tradition": "Kore modern (꿈해몽 사전)", "language": "ko", "domain": "", "url": url,
            "license": LICENSE, "rights_holder": RIGHTS, "attributed_author": "", "headword": word}
    rows = [{**base, "symbol_raw": word, "condition": "", "meaning": txt(head.group(2)), "polarity": pol(head.group(2)),
             "locator": f"{word} #intro"}]
    for i, (q, a) in enumerate(re.findall(
            r'<button class="btn btn-block[^>]*>(.*?)</button>.*?<div class="card-body">(.*?)</div>', page, re.S), 1):
        q, a = txt(q), txt(a)
        if q and a:
            rows.append({**base, "symbol_raw": q, "condition": word, "meaning": a, "polarity": pol(a),
                         "locator": f"{word} #{i}"})
    return rows


def main() -> None:
    f = Fetcher(Meta(SOURCE, LICENSE, RIGHTS, "Kore modern"), delay=1.5)
    urls = [u for u in sitemap_urls(f, SITE + "/sitemap.xml") if re.search(r"/dream-interpretation/[^/]+$", u)]
    kw = get_text(f, SITE + "/dream-interpretation-keywords") or ""
    urls += [SITE + h for h in re.findall(r'href="(/dream-interpretation/[^"#?]+)"', kw)]
    urls = list(dict.fromkeys(urls))
    print("urls", len(urls), flush=True)
    run(f, SOURCE, urls, parse, 12000)


if __name__ == "__main__":
    main()
