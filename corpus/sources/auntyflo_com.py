"""auntyflo.com: Auntyflo dream dictionary (modern English, commercial, Drupal).

Dream pages are taken from sitemap.xml (pages 1-4); search, tag and taxonomy
paths are disallowed in robots.txt and are never requested. Only
/dream-dictionary/<slug> nodes are fetched. Rows: one per bullet (bold lead as
condition) or paragraph of the node body, with the section heading in locator.
"""

from __future__ import annotations

import html
import json
import re

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "auntyflo.com"
BASE = "https://www.auntyflo.com"
META = Meta(
    source=SOURCE,
    license="copyrighted, all rights reserved (no reuse licence)",
    rights_holder="Auntyflo.com (operator, see notes.md)",
    tradition="modern-western-popular",
)
EXTRA = ["/", "/about", "/about-us", "/contact", "/terms-conditions", "/terms", "/privacy-policy"]

COND_RE = re.compile(
    r"^(.{3,160}?)\s+(?:indicates?|suggests?|signif(?:y|ies)|represents?|means?|refers?|denotes?|"
    r"symboli[sz]es?|implies|reflects?|is (?:a|an|symbolic)|foretells?|may (?:indicate|represent|suggest|mean|reflect|signify)|"
    r"could (?:indicate|represent|suggest|mean|reflect)|points? to)\b",
    re.I,
)


def clean(fragment: str) -> str:
    t = re.sub(r"(?is)<(script|style|svg|picture|figure).*?</\1>", " ", fragment)
    t = re.sub(r"(?i)<br\s*/?>", " ", t)
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
            print("BLOCKED", e, flush=True)
            return None
        except Exception as e:
            print("ERR", url, type(e).__name__, str(e)[:120], flush=True)
            return None
        self.paths[url] = f"files/{name}"
        return r.content.decode("utf-8", "replace")


def body_of(page: str) -> str:
    m = re.search(r'field-node--body[^>]*>', page)
    if not m:
        return ""
    rest = page[m.end():]
    stop = re.search(r'<div class="field field-node--(?!body)|</article>|<footer|class="node-links', rest)
    return rest[: stop.start()] if stop else rest


def parse(url: str, page: str) -> list[dict]:
    sm = re.search(r'<h2 class="node-title[^"]*"[^>]*>\s*<span>(.*?)</span>', page, re.S)
    symbol = clean(sm.group(1)) if sm else ""
    if not symbol:
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
        symbol = re.sub(r"(?i)\s*dream meaning\s*$", "", clean(h1.group(1))) if h1 else ""
    author = ""
    am = re.search(r'(?is)(?:class="[^"]*author[^"]*"[^>]*>|By\s*<a[^>]*>)\s*(?:<[^>]+>\s*)*([A-Z][A-Za-z .\'-]{2,40})<', page)
    if am:
        author = am.group(1).strip()
    body = body_of(page)
    rows: list[dict] = []
    section = ""
    n = 0
    for m in re.finditer(r"(?is)<(h[2-5]|p|li)\b[^>]*>(.*?)</\1>", body):
        tag, inner = m.group(1).lower(), m.group(2)
        if tag.startswith("h"):
            section = clean(inner)
            continue
        if tag == "li" and re.search(r"(?i)<(ul|ol)\b", inner):
            inner = re.split(r"(?i)<(?:ul|ol)\b", inner)[0]
        text = clean(inner)
        if len(text) < 12:
            continue
        cond = ""
        lead = re.match(r"(?is)\s*<(strong|b)>(.*?)</\1>", inner)
        if lead:
            cond = clean(lead.group(2)).strip(" -:–—")
        if not cond:
            cond = condition_of(text)
        n += 1
        rows.append({
            "source": SOURCE,
            "tradition": META.tradition,
            "language": "en",
            "symbol_raw": symbol,
            "condition": cond,
            "meaning": text,
            "polarity": "bilinmiyor",
            "domain": "",
            "url": url,
            "locator": f"{section} | {tag}{n}" if section else f"{tag}{n}",
            "license": META.license,
            "rights_holder": META.rights_holder,
            "attributed_author": author,
        })
    return rows


def main() -> None:
    f = Fetcher(META, delay=2.0)
    c = Cache(f)
    for p in EXTRA:
        c.get(BASE + p, "site_" + (p.strip("/") or "index") + ".html")
    urls: list[str] = []
    for i in range(1, 5):
        sm = c.get(f"{BASE}/sitemap.xml?page={i}", f"sitemap_{i}.xml") or ""
        for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm):
            if re.match(rf"{re.escape(BASE)}/dream-dictionary/[^/]{{2,}}$", u) and u not in urls:
                urls.append(u)
    print("sitemap dream nodes", len(urls), flush=True)
    out = ROOT / SOURCE / "entries.jsonl"
    if out.exists():
        out.unlink()
    rows: list[dict] = []
    for k, u in enumerate(urls):
        slug = re.sub(r"[^a-z0-9-]+", "_", u.rsplit("/", 1)[1].lower())[:120]
        page = c.get(u, f"dream_{slug}.html")
        if page:
            rows.extend(parse(u, page))
        if k % 100 == 0:
            print(k, len(rows), flush=True)
    write_entries(SOURCE, rows)
    print("pages", len(urls), "entries", len(rows), "symbols", len({r["symbol_raw"] for r in rows}))


if __name__ == "__main__":
    main()
