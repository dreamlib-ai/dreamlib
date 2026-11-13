"""星座屋 xzw.com 周公解梦 dictionary (Chinese, modern, commercial site).

robots.txt (checked by Fetcher) only disallows /xforum*, /xnews*, /sxpk*, /xzpk*.
Each headword page (/jiemeng/lib/<id>.html) has an intro paragraph and many
<dl><dt>梦见 <strong>X</strong></dt><dd>meaning</dd></dl> sub-entries.

Run: backend/.venv/Scripts/python -m corpus.sources.xzw_com
"""

from __future__ import annotations

import html
import re
import sys

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "xzw.com"
SITE = "https://www.xzw.com"
CATS = ["renwu", "dongwu", "zhiwu", "wupin", "shenti", "shenghuo", "huodong", "ziran", "qingai", "guishen",
        "jianzhu", "qita"]
CAT_NAMES = {"renwu": "人物", "dongwu": "动物", "zhiwu": "植物", "wupin": "物品", "shenti": "身体", "shenghuo": "生活",
             "huodong": "活动", "ziran": "自然", "qingai": "情爱", "guishen": "鬼神", "jianzhu": "建筑", "qita": "其他"}
LICENSE = "All rights reserved (commercial site; no open license stated)"
RIGHTS = "星座屋 www.xzw.com (ICP 粤ICP备11026234号-18, 粤B2-20160249)"
LIB = re.compile(r'href="(?:https://www\.xzw\.com)?/jiemeng/lib/(\d+)\.html"')


def text(fragment: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = re.sub(r"<script.*?</script>|<[^>]+>", "", t, flags=re.S)
    return re.sub(r"[ \t\r\f\v]+", " ", html.unescape(t)).strip()


def polarity(meaning: str) -> str:
    m = meaning.lstrip()
    if m.startswith(("大吉", "吉")):
        return "iyi"
    if m.startswith(("大凶", "凶")):
        return "kötü"
    return "bilinmiyor"


def parse(page: str, url: str, cat: str) -> list[dict]:
    head = re.search(r'<h2 class="title">(.*?)</h2>', page, re.S)
    if not head:
        return []
    title = text(head.group(1))
    headword = re.sub(r"^梦见", "", title)
    body = page[head.end():]
    end = body.find('<div class="jiemeilike')
    body = body[: end if end > 0 else len(body)]
    rows = []
    base = {
        "source": SOURCE, "tradition": "Çin modern (周公解梦 halk derlemesi)", "language": "zh-Hans",
        "domain": CAT_NAMES.get(cat, ""), "url": url, "license": LICENSE, "rights_holder": RIGHTS,
        "attributed_author": "", "headword": headword,
    }
    intro = text(re.sub(r"<dl>.*", "", body, flags=re.S).split('<div class="adb adb_3"')[0])
    intro = re.sub(r"setp_ad\(\d\)", "", intro).strip()
    if intro:
        rows.append({**base, "symbol_raw": title, "condition": "", "meaning": intro, "polarity": "bilinmiyor",
                     "locator": f"{title} #0"})
    for n, (dt, dd) in enumerate(re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", body, re.S), 1):
        sym = text(re.sub(r"<small>.*?</small>", "", dt, flags=re.S))
        meaning = text(dd)
        if not sym or not meaning:
            continue
        cond = ""
        m = re.match(r"^(.{1,8}?)梦(?:见|到)(.+)$", sym)
        if m and m.group(1) not in ("我", "自己", "昨晚"):
            cond = m.group(1)
        rows.append({**base, "symbol_raw": sym, "condition": cond, "meaning": meaning, "polarity": polarity(meaning),
                     "locator": f"{title} #{n}"})
    return rows


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition="Çin modern"), delay=1.5)
    files = ROOT / SOURCE / "files"
    ids: dict[str, str] = {}  # id -> category

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

    for cat in CATS:
        first = get_text(f"{SITE}/jiemeng/lib/{cat}/", f"list/{cat}-1.html")
        if not first:
            continue
        pages = [int(x) for x in re.findall(rf"/jiemeng/lib/{cat}/(\d+)\.html", first)]
        last = max(pages) if pages else 1
        found = LIB.findall(first)
        for p in range(2, last + 1):
            t = get_text(f"{SITE}/jiemeng/lib/{cat}/{p}.html", f"list/{cat}-{p}.html")
            if t:
                found += LIB.findall(t)
        for i in found:
            ids.setdefault(i, cat)
        print(cat, "pages", last, "ids so far", len(ids), flush=True)

    entries = ROOT / SOURCE / "entries.jsonl"
    if entries.exists():
        entries.unlink()
    queue = list(ids)
    done = set()
    total = 0
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 12000  # politeness cap on pages
    while queue:
        i = queue.pop(0)
        if i in done:
            continue
        done.add(i)
        url = f"{SITE}/jiemeng/lib/{i}.html"
        page = get_text(url, f"lib/{i}.html")
        if not page:
            continue
        rows = parse(page, url, ids.get(i, ""))
        write_entries(SOURCE, rows)
        total += len(rows)
        for j in LIB.findall(page):  # related headwords not reached from listings
            if j not in done and j not in ids:
                ids[j] = ""
                queue.append(j)
        if len(done) % 100 == 0:
            print("pages", len(done), "queue", len(queue), "entries", total, flush=True)
        if limit and len(done) >= limit:
            break
    print("done pages", len(done), "entries", total)


if __name__ == "__main__":
    main()
