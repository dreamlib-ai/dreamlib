"""Shared helpers for the dream-symbol / lottery-number slice.

Used by smorfia, primbon, somo, thai_dream, bicho, suenos, sonhos, reves,
traum, swapna, tabir and tabeer source scripts. Every request goes through
corpus.fetch.Fetcher. Pages already in the manifest are read back from disk,
so reruns only fetch what is missing; entries.jsonl is rebuilt from the saved
files on every run (write_entries appends, so the old file is removed first).
"""

from __future__ import annotations

import gzip
import hashlib
import html as htmlmod
import json
import re
import sys
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urljoin, urlparse, unquote

import httpx

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "dt", "dd", "blockquote", "div", "td", "th", "br", "table", "ul", "ol", "section", "article"}
SKIP_TAGS = {"script", "style", "noscript", "svg", "iframe", "form", "button", "select", "nav", "footer", "header", "aside"}


def log(*a) -> None:
    print(*a, flush=True)


# ---------------------------------------------------------------- html utils

class _Blocks(HTMLParser):
    """Flatten HTML into ordered blocks: (tag, text, strong_lead)."""

    def __init__(self, skip_nav: bool = True) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str, str]] = []
        self.buf: list[str] = []
        self.strong: list[str] = []
        self.in_strong = 0
        self.lead_open = False
        self.skip = 0
        self.tag = "p"
        self.skip_tags = SKIP_TAGS if skip_nav else {"script", "style", "noscript", "svg"}

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        lead = re.sub(r"\s+", " ", "".join(self.strong)).strip()
        if text:
            self.blocks.append((self.tag, text, lead))
        self.buf, self.strong = [], []
        self.lead_open = False

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in BLOCK_TAGS:
            self._flush()
            self.tag = tag
        if tag in ("strong", "b"):
            self.in_strong += 1
            if not "".join(self.buf).strip() and not self.strong:
                self.lead_open = True
        if tag in ("td", "th"):
            self.buf.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("strong", "b"):
            self.in_strong = max(0, self.in_strong - 1)
            if not self.in_strong:
                self.lead_open = False
        if tag in BLOCK_TAGS and tag not in ("td", "th"):
            self._flush()
            self.tag = "p"

    def handle_data(self, data):
        if self.skip:
            return
        self.buf.append(data)
        if self.in_strong and self.lead_open and len(self.strong) < 50:
            self.strong.append(data)  # bold text that opens the block

    def close(self):
        super().close()
        self._flush()


def blocks(html: str, skip_nav: bool = True) -> list[tuple[str, str, str]]:
    p = _Blocks(skip_nav)
    try:
        p.feed(html)
        p.close()
    except Exception:
        pass
    return p.blocks


def text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"[ \t\r\f\v]+", " ", htmlmod.unescape(html)).strip()


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(s or "")).strip()


def first(pattern: str, html: str, flags=re.I | re.S) -> str:
    m = re.search(pattern, html, flags)
    return clean(re.sub(r"(?s)<[^>]+>", " ", m.group(1))) if m else ""


def region(html: str, start_patterns: Iterable[str], end_patterns: Iterable[str] = ()) -> str:
    """Cut html from the first matching start pattern to the first end pattern after it."""
    for sp in start_patterns:
        m = re.search(sp, html, re.I | re.S)
        if m:
            sub = html[m.start():]
            best = len(sub)
            for ep in end_patterns:
                e = re.search(ep, sub[200:], re.I | re.S)
                if e:
                    best = min(best, e.start() + 200)
            return sub[:best]
    return ""


def h1(html: str) -> str:
    return first(r"<h1[^>]*>(.*?)</h1>", html) or first(r"<title[^>]*>(.*?)</title>", html)


# ------------------------------------------------------------- site runner

@dataclass
class Site:
    source: str
    tradition: str
    language: str
    license: str = "unknown (all rights reserved assumed)"
    rights_holder: str = "unknown"
    delay: float = 2.0
    sitemaps: list[str] = field(default_factory=list)
    url_re: str = ""            # pages to keep from sitemaps / crawl
    url_exclude: str = r"$^"
    seeds: list[str] = field(default_factory=list)
    follow_re: str = ""         # link-crawl: listing pages to follow (not parsed unless url_re matches)
    max_pages: int = 20000
    max_listing: int = 3000
    extra_urls: list[str] = field(default_factory=list)
    parse: Callable[[str, str], list[dict]] | None = None
    sitemap_child_re: str = ""  # only descend into child sitemaps matching this


def _name(url: str) -> str:
    p = urlparse(url)
    slug = unquote(p.path).strip("/").replace("/", "__") or "index"
    if p.query:
        slug += "__" + unquote(p.query)
    slug = re.sub(r"[^\w.\-]+", "_", slug, flags=re.U)
    if len(slug) > 90 or not slug.isascii():
        slug = re.sub(r"[^A-Za-z0-9._\-]+", "_", slug)[:60] + "_" + hashlib.sha1(url.encode()).hexdigest()[:12]
    return slug


class Runner:
    def __init__(self, site: Site) -> None:
        self.site = site
        self.f = Fetcher(Meta(source=site.source, license=site.license, rights_holder=site.rights_holder,
                              tradition=site.tradition), delay=site.delay)
        self.paths: dict[str, str] = {}
        if self.f.manifest.exists():
            for line in self.f.manifest.open(encoding="utf-8"):
                if line.strip():
                    row = json.loads(line)
                    self.paths[row["url"]] = row["path"]
        self.blocked_n = 0
        self.errors = 0

    # -- fetching
    def get(self, url: str, kind: str = "pages") -> str | None:
        """Return decoded body, from disk when already fetched."""
        if url in self.paths:
            p = self.f.dir / self.paths[url]
            if p.exists():
                return decode(p.read_bytes())
        try:
            r = self.f.get(url, name=f"{kind}/{_name(url)}")
        except Blocked as e:
            self.blocked_n += 1
            log("BLOCKED", url, e)
            return None
        except httpx.HTTPStatusError as e:
            self.errors += 1
            log("HTTP", e.response.status_code, url)
            return None
        except Exception as e:  # network / TLS
            self.errors += 1
            log("ERR", url, repr(e)[:160])
            self.f._block(url, f"network: {repr(e)[:120]}")
            return None
        if url in self.f._seen:
            self.paths[url] = f"{kind}/{_name(url)}"
        return decode(r.content, r.encoding)

    def sitemap_urls(self, url: str, depth: int = 0) -> list[str]:
        body = self.get(url, kind="sitemaps")
        if body is None:
            return []
        locs = [clean(x) for x in re.findall(r"<loc>\s*(.*?)\s*</loc>", body, re.S)]
        if "<sitemapindex" in body[:2000] or (locs and all(re.search(r"\.xml(\.gz)?($|\?)", l) for l in locs[:5])):
            out = []
            for l in locs:
                if self.site.sitemap_child_re and not re.search(self.site.sitemap_child_re, l):
                    continue
                out += self.sitemap_urls(l, depth + 1)
            return out
        return locs

    def discover(self) -> list[str]:
        s = self.site
        urls: list[str] = []
        for sm in s.sitemaps:
            for u in self.sitemap_urls(sm):
                if re.search(s.url_re, u) and not re.search(s.url_exclude, u):
                    urls.append(u)
        urls += s.extra_urls
        if s.seeds:
            urls += self.crawl()
        seen, out = set(), []
        for u in urls:
            u = u.split("#")[0]
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out[: s.max_pages]

    def crawl(self) -> list[str]:
        s = self.site
        queue, seen, pages = list(s.seeds), set(s.seeds), []
        n = 0
        while queue and n < s.max_listing:
            u = queue.pop(0)
            n += 1
            body = self.get(u, kind="listing")
            if body is None:
                continue
            for href in re.findall(r'href=["\']([^"\'#]+)', body):
                a = urljoin(u, htmlmod.unescape(href))
                if urlparse(a).netloc != urlparse(u).netloc:
                    continue
                if re.search(s.url_exclude, a):
                    continue
                if a in seen:
                    continue
                seen.add(a)
                if s.url_re and re.search(s.url_re, a):
                    pages.append(a)
                elif s.follow_re and re.search(s.follow_re, a):
                    queue.append(a)
        log(f"crawl: {n} listing pages, {len(pages)} item pages")
        return pages

    # -- running
    def run(self, fetch_only: bool = False) -> None:
        s = self.site
        log(f"[{s.source}] discovering")
        urls = self.discover()
        log(f"[{s.source}] {len(urls)} pages")
        rows: list[dict] = []
        t0 = time.time()
        for i, u in enumerate(urls):
            body = self.get(u)
            if i % 100 == 0:
                log(f"[{s.source}] {i}/{len(urls)} rows={len(rows)} {int(time.time()-t0)}s")
            if body is None or fetch_only or not s.parse:
                continue
            try:
                rows += self.finish(s.parse(u, body), u)
            except Exception as e:
                log("PARSE ERR", u, repr(e)[:200])
        if not fetch_only:
            self.write(rows)

    def finish(self, rows: list[dict], url: str) -> list[dict]:
        s = self.site
        out = []
        for r in rows:
            for k in ("symbol_raw", "condition", "meaning"):
                v = r.get(k) or ""
                if "&#" in v or "&amp;" in v or "&quot;" in v:
                    r[k] = htmlmod.unescape(v)
            if not (r.get("symbol_raw") or "").strip() or not ((r.get("meaning") or "").strip() or r.get("numbers")):
                continue
            row = {
                "source": s.source, "tradition": s.tradition, "language": s.language,
                "symbol_raw": clean(r.get("symbol_raw", ""))[:300], "condition": clean(r.get("condition", ""))[:500],
                "meaning": (r.get("meaning") or "").strip()[:8000], "polarity": r.get("polarity", "bilinmiyor"),
                "domain": r.get("domain", ""), "url": r.get("url", url), "locator": r.get("locator", ""),
                "license": s.license, "rights_holder": s.rights_holder, "attributed_author": r.get("attributed_author", ""),
            }
            if r.get("numbers"):
                row["numbers"] = r["numbers"]
            out.append(row)
        return out

    def write(self, rows: list[dict]) -> None:
        path = ROOT / self.site.source / "entries.jsonl"
        if path.exists():
            path.unlink()
        # de-duplicate identical rows
        seen, uniq = set(), []
        for r in rows:
            k = (r["symbol_raw"], r["condition"], r["meaning"][:200], str(r.get("numbers")))
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        write_entries(self.site.source, uniq)
        log(f"[{self.site.source}] wrote {len(uniq)} entries -> {path}")


def decode(b: bytes, enc: str | None = None) -> str:
    if b[:2] == b"\x1f\x8b":
        try:
            b = gzip.decompress(b)
        except Exception:
            pass
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', b[:3000])
    for e in ([m.group(1).decode()] if m else []) + ([enc] if enc else []) + ["utf-8", "cp1252"]:
        try:
            return b.decode(e)
        except Exception:
            continue
    return b.decode("utf-8", "replace")


def main(sites: dict[str, Site]) -> None:
    args = sys.argv[1:]
    fetch_only = "--fetch-only" in args
    names = [a for a in args if not a.startswith("--")] or list(sites)
    for n in names:
        try:
            Runner(sites[n]).run(fetch_only=fetch_only)
        except Exception as e:
            log(f"[{n}] FAILED {e!r}")


# ----------------------------------------------------------- generic parse

def split_conditions(bl: list[tuple[str, str, str]], lead_re: str) -> list[tuple[str, str]]:
    """Find 'Lead phrase: explanation' blocks (bold lead or colon form) matching lead_re."""
    out = []
    for tag, t, lead in bl:
        if tag in ("h1",):
            continue
        cond, mean = "", ""
        if lead and t.startswith(lead[:20]) and re.search(lead_re, lead, re.I) and len(t) > len(lead) + 10:
            cond, mean = lead, t[len(lead):]
        else:
            m = re.match(rf"\s*((?:{lead_re})[^:：.]{{2,140}})\s*[:：–\-]\s+(.{{15,}})", t, re.I | re.S)
            if m:
                cond, mean = m.group(1), m.group(2)
        cond = cond.strip(" :：-–—")
        mean = mean.strip(" :：-–—")
        if cond and mean:
            out.append((cond, mean))
    return out


def body_text(bl: list[tuple[str, str, str]], stop_re: str = r"$^", min_len: int = 30, limit: int = 6000) -> str:
    parts, n = [], 0
    for tag, t, _ in bl:
        if re.search(stop_re, t, re.I):
            break
        if tag == "h1" or len(t) < min_len and tag not in ("h2", "h3"):
            continue
        parts.append(t)
        n += len(t)
        if n > limit:
            break
    return "\n".join(parts)


def sections(bl: list[tuple[str, str, str]], heads: tuple[str, ...] = ("h2", "h3"), min_len: int = 1) -> list[tuple[str, str]]:
    """Group blocks under the preceding heading: [(heading, text)] (heading '' for the lead)."""
    out: list[tuple[str, list[str]]] = [("", [])]
    for tag, t, _ in bl:
        if tag == "h1":
            continue
        if tag in heads:
            out.append((t, []))
        elif len(t) >= min_len:
            out[-1][1].append(t)
    return [(h, "\n".join(ts)) for h, ts in out if ts]


AUTHORS = {
    "miller": "Gustavus Hindman Miller", "nostradamus": "Nostradamus (attrib.)", "artémidore": "Artemidorus",
    "artemidore": "Artemidorus", "freud": "Sigmund Freud", "jung": "Carl Gustav Jung",
    "ibn sirin": "Ibn Sirin", "ibn sîrîn": "Ibn Sirin", "nabulsi": "Abd al-Ghani al-Nabulsi",
    "ابن سیرین": "Ibn Sirin", "ابن سيرين": "Ibn Sirin", "امام صادق": "Imam Ja'far al-Sadiq",
    "جابر مغربی": "Jabir al-Maghribi", "دانیال": "Daniel (attrib.)", "منوچهر مطیعی": "Manouchehr Motiei",
    "یوسف نبی": "Yusuf (attrib.)", "حضرت یوسف": "Yusuf (attrib.)", "کرمانی": "Ibrahim Kirmani",
    "اسماعیل بن اشعث": "Ismail ibn Ash'ath", "لوک اویتنهاو": "Lucas Ouittenhove", "آنلی بیتون": "Anli Beaton",
}


def author_in(s: str) -> str:
    low = s.lower()
    for k, v in AUTHORS.items():
        if k in low:
            return v
    return ""
