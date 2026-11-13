"""Korean encyclopedic dream pages: 한국민족문화대백과사전 (encykorea.aks.ac.kr) and ko.wikipedia.org.

Only fixed article URLs (found by web search / known titles), fetched via Fetcher. ko.wikipedia /wiki/ HTML
is allowed by robots (the API is not). One row per section.
Run: backend/.venv/Scripts/python -m corpus.sources.kr_encyclopedic
"""
from __future__ import annotations

import html
import re
import sys
from urllib.parse import quote

from corpus.fetch import Fetcher, Meta
from corpus.sources.krjp_common import generic_rows, run

SOURCE = "kr-encyclopedic"
ENCY = ["E0011278", "E0058917", "E0048074", "E0028670", "E0032032", "E0008217", "E0018830", "E0079339"]
WIKI = ["해몽", "태몽", "꿈", "예지몽", "길몽", "흉몽", "악몽", "자각몽", "꿈풀이", "주공해몽", "초몽", "일장춘몽"]
HOLD = {"encykorea.aks.ac.kr": ("한국학중앙연구원 (AKS) 한국민족문화대백과사전; page footer: AKS copyright, 공공누리 (KOGL) per item mark, verify", "Kore ansiklopedik"),
        "ko.wikipedia.org": ("CC BY-SA 4.0 / GFDL", "Kore ansiklopedik (Wikipedia)")}


def parse_ency(page: str, url: str, base: dict) -> list[dict]:
    t = lambda x: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()  # noqa: E731
    title = re.search(r'<div class="subject">\s*<h3>(.*?)</h3>', page, re.S)
    author = re.search(r'<li class="author">\s*<a[^>]*>(.*?)</a>', page, re.S)
    word = t(title.group(1)) if title else ""
    base = {**base, "attributed_author": t(author.group(1)) if author else "", "headword": word}
    rows = []
    for sid, sec in re.findall(r'<section id="(\w+)" class="content_section[^"]*">(.*?)</section>', page, re.S):
        if sid == "meta":
            continue
        head = re.search(r'<h3 class="tit">(.*?)</h3>', sec, re.S)
        ps = [t(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", sec, re.S)]
        body = chr(10).join(p for p in ps if p)
        if body and len(body) > 30:
            rows.append({**base, "symbol_raw": word, "condition": t(head.group(1)) if head else sid, "meaning": body,
                         "polarity": "bilinmiyor", "url": url, "locator": f"{word} #{sid}"})
    return rows


def main() -> None:
    f = Fetcher(Meta(SOURCE, "mixed: see rows", "mixed: see rows", "Kore ansiklopedik"), delay=2.0)
    urls = [f"https://encykorea.aks.ac.kr/Article/{i}" for i in ENCY] + \
           [f"https://ko.wikipedia.org/wiki/{quote(t)}" for t in WIKI]

    def parse(page: str, url: str) -> list[dict]:
        host = url.split("/")[2]
        lic, trad = HOLD[host]
        base = {"source": SOURCE, "tradition": trad, "language": "ko", "domain": "ansiklopedi",
                "license": lic if host == "ko.wikipedia.org" else "unclear: " + lic,
                "rights_holder": "Wikipedia contributors" if host == "ko.wikipedia.org" else lic.split(";")[0],
                "attributed_author": ""}
        if host == "ko.wikipedia.org":
            return generic_rows(page, url, base, lambda s: s, min_len=30, block_cls="mw-parser-output")
        return parse_ency(page, url, base)

    run(f, SOURCE, urls, parse, 200)


if __name__ == "__main__":
    main()
