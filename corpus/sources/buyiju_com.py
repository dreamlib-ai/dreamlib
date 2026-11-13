"""卜易居 buyiju.com 周公解梦 (Chinese, modern, commercial site).

robots.txt allows `*` (and does not name ClaudeBot/anthropic-ai) but disallows
GPTBot, CCBot, Amazonbot and many SEO bots; recorded in notes.md.
Headword pages /zgjm/<cat>/<id>.html hold <p><strong>梦见X</strong>：meaning</p> items.

Run: backend/.venv/Scripts/python -m corpus.sources.buyiju_com
"""

from __future__ import annotations

import html
import re
import sys

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "buyiju.com"
SITE = "https://www.buyiju.com"
CATS = {"yuanban": "原版周公解梦", "zhouyi": "周易解梦", "mengzhao": "梦兆吉凶", "renwu": "人物篇", "dongwu": "动物篇",
        "zhiwu": "植物篇", "dongzuo": "动作篇", "wupin": "物品篇", "jianzhu": "建筑篇", "ziran": "自然篇",
        "guishen": "鬼神篇", "shenghuo": "生活篇", "shenti": "身体篇", "qita": "其它篇"}
LICENSE = "All rights reserved (Copyright © 2006-2026 www.Buyiju.Com 版权所有)"
RIGHTS = "卜易居 www.buyiju.com"
ITEM = re.compile(r'href="(?:https://www\.buyiju\.com)?/zgjm/([a-z]+)/(\d+)\.html"')


def text(fragment: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = re.sub(r"<script.*?</script>|<[^>]+>", "", t, flags=re.S)
    return re.sub(r"[ \t\r\f\v]+", " ", html.unescape(t)).strip()


def polarity(meaning: str) -> str:
    m = meaning.lstrip("：: ")
    if m.startswith(("大吉", "吉")):
        return "iyi"
    if m.startswith(("大凶", "凶")):
        return "kötü"
    return "bilinmiyor"


def parse(page: str, url: str, cat: str) -> list[dict]:
    head = re.search(r'<div class="title"><h2>(.*?)</h2>', page, re.S)
    title = text(head.group(1)) if head else ""
    start = page.find('<div class="content">')
    end = page.find('<div class="vipcontainer">', start)
    if start < 0:
        return []
    body = page[start: end if end > 0 else len(page)]
    base = {
        "source": SOURCE, "tradition": "Çin modern (周公解梦 halk derlemesi)", "language": "zh-Hans",
        "domain": CATS.get(cat, ""), "url": url, "license": LICENSE, "rights_holder": RIGHTS, "attributed_author": "",
        "headword": re.sub(r"^梦(?:见|到)", "", title),
    }
    rows = []
    n = 0
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        m = re.match(r"\s*(?:<img[^>]*>\s*)*<strong>(.*?)</strong>(.*)$", p, re.S)
        if not m:
            continue
        sym = text(m.group(1)).rstrip("：:")
        meaning = text(m.group(2)).lstrip("：: ")
        if not sym or not meaning:
            continue
        n += 1
        cond = ""
        c = re.match(r"^(.{1,8}?)梦(?:见|到)(.+)$", sym)
        if c and c.group(1) not in ("我", "自己", "做"):
            cond = c.group(1)
        rows.append({**base, "symbol_raw": sym, "condition": cond, "meaning": meaning, "polarity": polarity(meaning),
                     "locator": f"{title} #{n}"})
    if not rows and title:
        # Q&A style pages (梦兆吉凶): keep the whole answer under the title
        paras = [text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S)]
        joined = "\n".join(x for x in paras if x)
        if joined:
            rows.append({**base, "symbol_raw": title, "condition": "", "meaning": joined, "polarity": "bilinmiyor",
                         "locator": f"{title} #0"})
    return rows


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition="Çin modern"), delay=1.5)
    files = ROOT / SOURCE / "files"

    def get_text(url: str, name: str) -> str | None:
        path = files / name
        if f.seen(url) and path.exists():
            return path.read_bytes().decode("utf-8", errors="replace")
        try:
            return f.get(url, name=name).text
        except Blocked as e:
            print("blocked", url, e)
        except Exception as e:  # noqa: BLE001
            print("error", url, repr(e)[:120])
        return None

    items: dict[tuple[str, str], None] = {}
    for cat in CATS:
        first = get_text(f"{SITE}/zgjm/{cat}/", f"list/{cat}-1.html")
        if not first:
            continue
        m = re.findall(rf"/zgjm/{cat}/list_(\d+)_(\d+)\.html", first)
        last = max((int(p) for _, p in m), default=1)
        lid = m[0][0] if m else ""
        pages = [first]
        for p in range(2, last + 1):
            t = get_text(f"{SITE}/zgjm/{cat}/list_{lid}_{p}.html", f"list/{cat}-{p}.html")
            if t:
                pages.append(t)
        for t in pages:
            for c, i in ITEM.findall(t):
                items.setdefault((c, i), None)
        print(cat, "pages", last, "items so far", len(items), flush=True)

    entries = ROOT / SOURCE / "entries.jsonl"
    if entries.exists():
        entries.unlink()
    queue = list(items)
    done: set[tuple[str, str]] = set()
    total = 0
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 8000  # politeness cap on pages
    while queue:
        key = queue.pop(0)
        if key in done:
            continue
        done.add(key)
        cat, i = key
        url = f"{SITE}/zgjm/{cat}/{i}.html"
        page = get_text(url, f"{cat}/{i}.html")
        if not page:
            continue
        rows = parse(page, url, cat)
        write_entries(SOURCE, rows)
        total += len(rows)
        for k in ITEM.findall(page):
            if k not in done and k not in items and k[0] in CATS:
                items[k] = None
                queue.append(k)
        if len(done) % 100 == 0:
            print("pages", len(done), "queue", len(queue), "entries", total, flush=True)
        if limit and len(done) >= limit:
            break
    print("done pages", len(done), "entries", total)


if __name__ == "__main__":
    main()
