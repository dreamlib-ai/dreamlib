"""Japanese dream-dictionary sites crawled with the generic section extractor.

Sites (all robots-allowed; Fetcher checks for us, ClaudeBot included):
  yumebunseki  夢分析研究所 yumebunseki.jp  (WordPress, post sitemaps, /yume-* articles)
  mikazuki     Mikazuki 夢占い luxisworks.com/mikazuki/dream/ (sitemap-pages.xml)
  yumedic      ユメディク yumedic.jp (no sitemap; crawl links from the home page)
Run: backend/.venv/Scripts/python -m corpus.sources.jp_blogs <yumebunseki|mikazuki|yumedic> [cap]
"""
from __future__ import annotations

import re
import sys

from corpus.fetch import Fetcher, Meta
from corpus.sources.krjp_common import generic_rows, get_text, run, sitemap_urls

LIC = "All rights reserved (no open license stated)"


def clean_title(t: str) -> str:
    t = re.sub(r"【[^】]*】", "", t)
    t = re.split(r"[｜|\-－–]", t)[0]
    return re.sub(r"\d+選", "", t).strip()


SITES = {
    "yumebunseki": dict(source="yumebunseki.jp", rights="夢分析研究所 yumebunseki.jp", site="https://yumebunseki.jp",
                        seeds=["https://yumebunseki.jp/sitemap_index.xml"], pat=r"yumebunseki\.jp/yume-[^/]+/?$"),
    "mikazuki": dict(source="luxisworks.com-mikazuki", rights="Mikazuki (luxisworks.com)", site="https://luxisworks.com",
                     seeds=["https://luxisworks.com/sitemap-pages.xml"], pat=r"/mikazuki/dream/[^/]+/$"),
    "yumedic": dict(source="yumedic.jp", rights="ユメディク yumedic.jp", site="https://yumedic.jp", seeds=[], pat=r""),
}


def main() -> None:
    key = sys.argv[1]
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
    c = SITES[key]
    f = Fetcher(Meta(c["source"], LIC, c["rights"], "Japonya modern"), delay=1.5)
    urls: list[str] = []
    for s in c["seeds"]:
        urls += [u for u in sitemap_urls(f, s) if re.search(c["pat"], u)]
    if key == "yumedic":
        home = get_text(f, c["site"] + "/") or ""
        seen = set()
        queue = [c["site"] + "/"]
        while queue and len(urls) < cap:
            u = queue.pop(0)
            if u in seen:
                continue
            seen.add(u)
            page = get_text(f, u) or ""
            urls.append(u)
            for h in re.findall(r'href="((?:https://yumedic\.jp)?/[^"#?]*)"', page):
                h = h if h.startswith("http") else c["site"] + h
                if h not in seen and not re.search(r"\.(css|js|png|jpg|svg|xml|webp)$", h):
                    queue.append(h)
    urls = list(dict.fromkeys(urls))
    print(key, "urls", len(urls), flush=True)
    base = {"source": c["source"], "tradition": "Japonya modern (夢占い)", "language": "ja", "domain": "",
            "license": LIC, "rights_holder": c["rights"], "attributed_author": ""}
    run(f, c["source"], urls, lambda page, url: generic_rows(page, url, base, clean_title,
        skip_heads=("目次", "まとめ", "関連", "この記事", "監修", "編集方針", "参考")), cap, reset=True)


if __name__ == "__main__":
    main()
