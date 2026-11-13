"""Shared crawl loop for the Korea/Japan dream sources (stdlib + corpus.fetch only).

`run(...)` takes a list of URLs, fetches each through Fetcher (cached on disk, resumable),
parses it with a per-site parse function and appends rows to entries.jsonl.
`sitemap_urls(f, url)` follows sitemap indexes. `generic_rows(...)` turns an article into
one row per heading (h2-h5 or bold-lead paragraph), intro under the page title.
"""

from __future__ import annotations

import re
import sys
from typing import Callable

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries
from corpus.sources import tr_common as tc


def sitemap_urls(f: Fetcher, url: str, depth: int = 0) -> list[str]:
    try:
        t = f.get(url, name=None, save=False).text
    except Exception as e:  # noqa: BLE001
        print("sitemap err", url, repr(e)[:100])
        return []
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", t)
    out: list[str] = []
    for u in locs:
        if u.endswith((".xml", ".xml.gz")) and depth < 2:
            out += sitemap_urls(f, u, depth + 1)
        else:
            out.append(u)
    return out


def fname(url: str) -> str:
    import hashlib
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]  # non-ASCII slugs would otherwise collide
    return "p/" + re.sub(r"[^0-9A-Za-z_.-]+", "_", re.sub(r"^https?://", "", url))[:120] + "_" + h + ".html"


def get_text(f: Fetcher, url: str, name: str | None = None) -> str | None:
    name = name or fname(url)
    path = f.dir / "files" / name
    if f.seen(url) and path.exists():
        return path.read_bytes().decode("utf-8", errors="replace")
    try:
        r = f.get(url, name=name)
        return r.text
    except Blocked as e:
        print("blocked", url, e, flush=True)
    except Exception as e:  # noqa: BLE001
        print("error", url, repr(e)[:120], flush=True)
    return None


def generic_rows(page: str, url: str, base: dict, strip_title: Callable[[str], str] = lambda s: s,
                 skip_heads: tuple[str, ...] = (), min_len: int = 20, block_cls: str = "") -> list[dict]:
    root = tc.parse(page)
    title = tc.h1(root)
    block = (tc.find(root, cls=block_cls) if block_cls else None) or tc.main_block(root, 150)
    if not title or block is None:
        return []
    word = strip_title(title)
    rows = []
    for n, (head, anchor, paras) in enumerate(tc.sections(block, bold_heads=False)):
        meaning = "\n".join(paras).strip()
        if len(meaning) < min_len or any(s in head for s in skip_heads):
            continue
        rows.append({**base, "symbol_raw": head or word, "condition": word if head else "", "meaning": meaning,
                     "polarity": "bilinmiyor", "url": url, "locator": f"{title} #{n}", "headword": word})
    return rows


def run(f: Fetcher, source: str, urls: list[str], parse: Callable[[str, str], list[dict]], cap: int = 12000,
        reset: bool = True) -> None:
    entries = ROOT / source / "entries.jsonl"
    if reset and entries.exists():
        entries.unlink()
    total = n = 0
    for u in urls[:cap]:
        page = get_text(f, u)
        n += 1
        if page:
            rows = parse(page, u)
            write_entries(source, rows)
            total += len(rows)
        if n % 100 == 0:
            print("pages", n, "of", min(len(urls), cap), "entries", total, flush=True)
    print("done pages", n, "entries", total, flush=True)
