"""ruyatabirleri.com: full crawl through the Yoast post sitemaps.

Each post is `/ruyada-<sembol>-gormek.html`; the article body holds an intro
(the base symbol) and `<h2>` sub-sections (condition variants). User comments
are not extracted.

Usage (repo root):
    backend/.venv/Scripts/python -m corpus.sources.ruyatabirleri_com            # crawl + extract
    backend/.venv/Scripts/python -m corpus.sources.ruyatabirleri_com extract    # extract only
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from corpus.fetch import Blocked, Fetcher, Meta, ROOT, write_entries

SOURCE = "ruyatabirleri-com"
BASE = "https://www.ruyatabirleri.com"
META = Meta(
    source=SOURCE,
    license="Tüm hakları saklıdır (© RuyaTabirleri.com)",
    rights_holder="RuyaTabirleri.com (site sahibi; şirket künyesi yok)",
    tradition="turk-modern",
)
EXTRA_PAGES = ["/ruya-nedir", "/istihare-hakkinda", "/islamiyet-ve-ruyalar", "/ruya-yorumlama-ve-ruya-tabiri",
               "/kabus-ve-karabasan-nedir", "/psikolojik-ruya-yorumlari", "/gizlilik-politikasi", "/iletisim"]


def clean(fragment: str) -> str:
    s = re.sub(r"<(script|style|aside)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v ]+", " ", s)
    s = re.sub(r" +([,.;:!?)])", r"\1", s)
    return s.strip()


def slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1] or "index"


def parse_post(text: str, url: str) -> list[dict]:
    m = re.search(r'<div class="article-body">(.*?)</div>\s*(?:<aside class="comment-invite"|<aside class="related-box"|<nav class="tag-row"|</article>)',
                  text, re.S)
    if not m:
        m = re.search(r'<div class="article-body">(.*?)</article>', text, re.S)
    if not m:
        return []
    body = m.group(1)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    title = clean(h1.group(1)) if h1 else ""
    headline = ""
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        for node in data.get("@graph", [data]) if isinstance(data, dict) else []:
            if isinstance(node, dict) and node.get("@type") == "Article" and node.get("headline"):
                headline = node["headline"]
                break
    symbol = headline or re.sub(r"^Rüyada\s+", "", title)
    # split on h2/h3 headings
    parts = re.split(r"(<h[23][^>]*>.*?</h[23]>)", body, flags=re.S)
    rows = []
    cond, anchor, buf = "", "giris", []

    def flush() -> None:
        paras = [clean(p) for p in re.findall(r"<(?:p|li)[^>]*>(.*?)</(?:p|li)>", "".join(buf), re.S)]
        paras = [p for p in paras if p]
        if not paras:
            loose = clean("".join(buf))
            paras = [loose] if loose else []
        if paras:
            rows.append({
                "source": SOURCE, "tradition": META.tradition, "language": "tr",
                "symbol_raw": symbol, "condition": cond, "meaning": "\n".join(paras),
                "polarity": "", "domain": "", "url": url, "locator": f"#{anchor}" if anchor != "giris" else "giriş",
                "license": META.license, "rights_holder": META.rights_holder, "attributed_author": "",
                "title": title,
            })

    for part in parts:
        hm = re.match(r"<h[23]([^>]*)>(.*?)</h[23]>", part, re.S)
        if hm:
            flush()
            buf = []
            cond = clean(hm.group(2))
            idm = re.search(r'id="([^"]+)"', hm.group(1))
            anchor = idm.group(1) if idm else cond
        else:
            buf.append(part)
    flush()
    return rows


def post_urls(f: Fetcher) -> list[str]:
    idx = f.get(f"{BASE}/sitemap_index.xml", name="sitemaps/sitemap_index.xml").text
    urls: list[str] = []
    for sm in re.findall(r"<loc>(.*?)</loc>", idx):
        if "/post-sitemap" not in sm:
            continue
        t = f.get(sm, name=f"sitemaps/{slug_of(sm)}").text
        urls += re.findall(r"<loc>(.*?)</loc>", t)
    return list(dict.fromkeys(urls))


def crawl() -> None:
    f = Fetcher(META, delay=1.5)
    for p in EXTRA_PAGES:
        try:
            f.get(BASE + p, name=f"pages/{slug_of(p)}.html")
        except Exception as e:  # noqa: BLE001
            print("page fail", p, e)
    urls = post_urls(f)
    print("post urls:", len(urls), flush=True)
    for i, u in enumerate(urls):
        if f.seen(u):
            continue
        try:
            f.get(u, name=f"posts/{slug_of(u)}")
        except Blocked as e:
            print("BLOCKED", e, flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print("fail", u, e, flush=True)
            with (f.dir / "errors.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"url": u, "error": str(e)}, ensure_ascii=False) + "\n")
        if i % 200 == 0:
            print(i, "/", len(urls), flush=True)


def extract() -> None:
    d = ROOT / SOURCE
    out = d / "entries.jsonl"
    if out.exists():
        out.unlink()
    rows: list[dict] = []
    n_posts = 0
    with (d / "manifest.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if not rec["path"].startswith("files/posts/"):
                continue
            n_posts += 1
            text = (d / rec["path"]).read_text(encoding="utf-8", errors="replace")
            rows += parse_post(text, rec["url"])
            if len(rows) > 5000:
                write_entries(SOURCE, rows)
                rows = []
    write_entries(SOURCE, rows)
    total = sum(1 for _ in out.open(encoding="utf-8"))
    print("posts:", n_posts, "entries:", total)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "crawl":
        crawl()
    extract()
