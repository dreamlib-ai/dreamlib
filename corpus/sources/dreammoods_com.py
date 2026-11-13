"""dreammoods.com: Dream Moods A-Z dream dictionary (modern English, commercial).

Crawls the letter pages (a.htm, a2.htm, ...) through corpus.fetch.Fetcher and
extracts one row per interpretation paragraph under each bold symbol heading.
Copyrighted site (Dream Moods, Inc., all rights reserved): raw data stays local
and is for research/inventory only until rights are negotiated.
"""

from __future__ import annotations

import html
import json
import re
import string

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "dreammoods.com"
BASE = "https://www.dreammoods.com"
META = Meta(
    source=SOURCE,
    license="copyrighted, all rights reserved (no reuse licence)",
    rights_holder="Dream Moods, Inc.",
    tradition="modern-western-popular",
)
EXTRA = ["/", "/reference/copyright.htm", "/reference/sitemap.htm", "/reference/contact.htm",
         "/reference/aboutus.htm", "/reference/privacy.htm"]

COND_RE = re.compile(
    r"^(.{3,160}?)\s+(?:indicates?|suggests?|signif(?:y|ies)|represents?|means?|refers?|denotes?|"
    r"symboli[sz]es?|implies|reflects?|is (?:a|an|symbolic)|foretells?|portends?|may (?:indicate|represent|suggest|mean|refer|signify)|"
    r"could (?:indicate|represent|suggest|mean)|can (?:indicate|represent|suggest|mean)|points? to|highlights?)\b",
    re.I,
)


def clean(fragment: str) -> str:
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", fragment)
    t = re.sub(r"(?i)<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def condition_of(text: str) -> str:
    if not re.match(r"(?i)^(to|if|when|dreaming|seeing|in your dream|in the dream)\b", text):
        return ""
    m = COND_RE.match(text)
    return m.group(1).strip(" ,") if m else ""


class Cache:
    def __init__(self, f: Fetcher) -> None:
        self.f = f
        self.paths: dict[str, str] = {}
        if f.manifest.exists():
            for line in f.manifest.open(encoding="utf-8"):
                if line.strip():
                    row = json.loads(line)
                    self.paths[row["url"]] = row["path"]

    def get(self, url: str, name: str) -> str | None:
        if url in self.paths:
            return (self.f.dir / self.paths[url]).read_bytes().decode("latin-1")
        try:
            r = self.f.get(url, name=name)
        except Blocked as e:
            print("BLOCKED", e)
            return None
        except Exception as e:  # 404 etc.
            print("ERR", url, type(e).__name__, str(e)[:120])
            return None
        self.paths[url] = f"files/{name}"
        return r.content.decode("latin-1")


def crawl(c: Cache) -> list[tuple[str, str]]:
    pages: list[tuple[str, str]] = []
    for p in EXTRA:
        c.get(BASE + p, "site" + (p.replace("/", "_") or "_index") + ("" if p.endswith(".htm") else ".html"))
    for letter in string.ascii_lowercase:
        url = f"{BASE}/dreamdictionary/{letter}.htm"
        body = c.get(url, f"dict_{letter}.htm")
        if body is None:
            continue
        pages.append((url, body))
        subs = sorted(set(re.findall(rf"dreamdictionary/({letter}\d+)\.htm", body)), key=lambda s: int(s[1:]))
        seen = {letter}
        queue = list(subs)
        while queue:
            s = queue.pop(0)
            if s in seen:
                continue
            seen.add(s)
            u = f"{BASE}/dreamdictionary/{s}.htm"
            b = c.get(u, f"dict_{s}.htm")
            if b is None:
                continue
            pages.append((u, b))
            for more in re.findall(rf"dreamdictionary/({letter}\d+)\.htm", b):
                if more not in seen:
                    queue.append(more)
        print(letter, "pages", len(seen), flush=True)
    return pages


HEAD_RE = re.compile(r'(?is)^\s*<b>\s*<font[^>]*size="?4"?[^>]*>(.*?)</font>\s*</b>\s*$')


def parse(url: str, body: str) -> list[dict]:
    rows: list[dict] = []
    symbol = ""
    n = 0
    for block in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", body):
        inner = block.strip()
        m = HEAD_RE.match(inner)
        if m:
            symbol = clean(m.group(1))
            n = 0
            continue
        if not symbol:
            continue
        text = clean(re.sub(r'(?is)<a href="#Top">.*?</a>', " ", inner))
        if len(text) < 15 or text.upper() == "TOP":
            continue
        if text.startswith("Dream Moods") or "Copyright" in text[:40]:
            symbol = ""
            continue
        n += 1
        rows.append({
            "source": SOURCE,
            "tradition": META.tradition,
            "language": "en",
            "symbol_raw": symbol,
            "condition": condition_of(text),
            "meaning": text,
            "polarity": "bilinmiyor",
            "domain": "",
            "url": url,
            "locator": f"{url.rsplit('/', 1)[1]}#{symbol} p{n}",
            "license": META.license,
            "rights_holder": META.rights_holder,
            "attributed_author": "Dream Moods, Inc.",
        })
    return rows


def main() -> None:
    f = Fetcher(META, delay=2.0)
    c = Cache(f)
    pages = crawl(c)
    out = ROOT / SOURCE / "entries.jsonl"
    if out.exists():
        out.unlink()
    rows: list[dict] = []
    for url, body in pages:
        rows.extend(parse(url, body))
    write_entries(SOURCE, rows)
    print("pages", len(pages), "entries", len(rows), "symbols", len({r["symbol_raw"] for r in rows}))


if __name__ == "__main__":
    main()
