"""dreambible.com: Dream Bible A-Z dream dictionary (modern English, commercial).

Letter pages are listed in the site's sitemap.xml and carry the full entries
inline, so only those pages (plus contact/about pages) are fetched. /forum/ is
disallowed for some bots and is never touched. One row per paragraph.
"""

from __future__ import annotations

import html
import json
import re

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "dreambible.com"
BASE = "https://www.dreambible.com"
META = Meta(
    source=SOURCE,
    license="copyrighted (Copyright 2010-2026, registered with CIPO/UKIPO/US LoC), no reuse licence",
    rights_holder="Dream Bible (dreambible.com operator; legal name not published)",
    tradition="modern-western-popular",
)
EXTRA = ["/contact.html", "/privacy.html", "/about.html", "/terms.html"]

COND_RE = re.compile(
    r"^(.{3,160}?)\s+(?:indicates?|suggests?|signif(?:y|ies)|represents?|means?|refers?|denotes?|"
    r"symboli[sz]es?|implies|reflects?|is (?:a|an|symbolic)|foretells?|may (?:indicate|represent|suggest|mean|reflect|signify)|"
    r"could (?:indicate|represent|suggest|mean|reflect)|points? to)\b",
    re.I,
)


def clean(fragment: str) -> str:
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", fragment)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def condition_of(text: str) -> str:
    if not re.match(r"(?i)^(to|if|when|dreaming|seeing)\b", text):
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
            return (self.f.dir / self.paths[url]).read_bytes().decode("utf-8", "replace")
        try:
            r = self.f.get(url, name=name)
        except Blocked as e:
            print("BLOCKED", e)
            return None
        except Exception as e:
            print("ERR", url, type(e).__name__, str(e)[:120])
            return None
        self.paths[url] = f"files/{name}"
        return r.content.decode("utf-8", "replace")


ANCHOR = re.compile(r'<a\s+style="padding-top:\s*80px;"\s+name="([^"]*)"\s*>\s*</a>', re.I)


def parse(url: str, body: str) -> list[dict]:
    rows: list[dict] = []
    marks = list(ANCHOR.finditer(body))
    page = url.rsplit("/", 1)[1]
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        chunk = body[m.end():end]
        stop = re.search(r"(?i)</blockquote>|</td>", chunk)
        if stop:
            chunk = chunk[: stop.start()]
        blocks = re.findall(r"(?is)<p\b[^>]*>(.*?)(?=</p>|<p\b|$)", chunk)
        if not blocks:
            continue
        symbol = clean(blocks[0]) or html.unescape(m.group(1)).strip()
        text_html = " ".join(blocks[1:])
        paras = [clean(p) for p in re.split(r"(?i)(?:<br\s*/?>\s*){2,}", text_html)]
        n = 0
        for p in paras:
            if len(p) < 3:
                continue
            n += 1
            rows.append({
                "source": SOURCE,
                "tradition": META.tradition,
                "language": "en",
                "symbol_raw": symbol,
                "condition": condition_of(p),
                "meaning": p,
                "polarity": "bilinmiyor",
                "domain": "",
                "url": f"{url}#{m.group(1)}",
                "locator": f"{page}#{m.group(1)} p{n}" + (" (example)" if p.lower().startswith("example") else ""),
                "license": META.license,
                "rights_holder": META.rights_holder,
                "attributed_author": "Dream Bible",
            })
    return rows


def main() -> None:
    f = Fetcher(META, delay=2.0)
    c = Cache(f)
    for p in EXTRA:
        c.get(BASE + p, "site_" + p.strip("/"))
    sm = c.get(BASE + "/sitemap.xml", "sitemap.xml") or ""
    urls = [u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm) if "/dreamdictionary/" in u]
    print("sitemap letter pages", len(urls), flush=True)
    out = ROOT / SOURCE / "entries.jsonl"
    if out.exists():
        out.unlink()
    rows: list[dict] = []
    for u in urls:
        body = c.get(u, "dict_" + u.rsplit("/", 1)[1])
        if body:
            got = parse(u, body)
            rows.extend(got)
            print(u.rsplit("/", 1)[1], len(got), flush=True)
    write_entries(SOURCE, rows)
    print("pages", len(urls), "entries", len(rows), "symbols", len({r["symbol_raw"] for r in rows}))


if __name__ == "__main__":
    main()
