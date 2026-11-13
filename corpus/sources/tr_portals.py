"""Turkish news / lifestyle portals with a dream-interpretation section.

One raw folder per portal (`raw/<portal>/`). Only portals whose robots.txt lets
our agent, ClaudeBot and anthropic-ai in are crawled; the Fetcher enforces it.

Usage (repo root):
    backend/.venv/Scripts/python -m corpus.sources.tr_portals <portal> [extract]
    portals: sabah takvim haberturk haberler-com mynet elele onedio blocked
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from urllib.parse import urljoin

from corpus.fetch import Blocked, Fetcher, Meta, ROOT, write_entries
from corpus.sources import tr_common as T

LIC = "Tüm hakları saklıdır (telifli haber/portal içeriği)"

PORTALS: dict[str, dict] = {
    "sabah": {"base": "https://www.sabah.com.tr", "rights": "Turkuvaz Haberleşme ve Yayıncılık A.Ş. (Sabah)"},
    "takvim": {"base": "https://www.takvim.com.tr", "rights": "Turkuvaz Medya Grubu (Takvim)"},
    "haberturk": {"base": "https://www.haberturk.com", "rights": "Habertürk (Ciner Yayın Holding)"},
    "haberler-com": {"base": "https://www.haberler.com", "rights": "Haberler.com"},
    "mynet": {"base": "https://www.mynet.com", "rights": "Mynet A.Ş."},
    "elele": {"base": "https://www.elele.com.tr", "rights": "Elele (Hearst/Doğan Burda lisansı; künyeye bakınız)"},
    "onedio": {"base": "https://onedio.com", "rights": "Onedio (Medya Onedio)"},
}

# robots-blocked portals asked for in the brief; one attempt each so they land in blocked.jsonl
BLOCKED_PROBES = {
    "ntv": "https://www.ntv.com.tr/yasam",
    "posta": "https://www.posta.com.tr/ruya-tabirleri",
    "hurriyet": "https://www.hurriyet.com.tr/mahmure/ruya-tabirleri/",
    "milliyet": "https://www.milliyet.com.tr/pembenar/ruya-tabirleri/",
    "cnnturk": "https://www.cnnturk.com/astroloji/ruya-tabirleri/",
    "aksam": "https://www.aksam.com.tr/ruya-tabirleri",
    "cumhuriyet": "https://www.cumhuriyet.com.tr/",
}


def locs(xml: str) -> list[str]:
    return [u.strip() for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, re.S)]


def links(doc: str, base: str) -> list[str]:
    return list(dict.fromkeys(urljoin(base, h.replace("&amp;", "&")) for h in re.findall(r'href="([^"#]+)"', doc)))


# ---------------------------------------------------------------- discovery

def turkuvaz_archives(f: Fetcher, base: str, prefix: str, since: int = 2018) -> list[str]:
    """Scan monthly post sitemap archives (Sabah/Takvim CMS) for URLs under prefix."""
    out: list[str] = []
    idx = f.get(f"{base}/sitemap/post.xml", name="sitemaps/post.xml").text
    for sm in locs(idx):
        m = re.search(r"/(\d{4})-\d+(?:-\d+)?\.xml$", sm)
        if not m or int(m.group(1)) < since:
            continue
        try:
            t = f.get(sm, save=False).text
        except Exception as e:  # noqa: BLE001
            print("sitemap fail", sm, e, flush=True)
            continue
        hits = [u for u in locs(t) if prefix in u and "/galeri/" not in u]
        out += hits
        if hits:
            print(sm, len(hits), flush=True)
    return out


def discover(name: str, f: Fetcher) -> list[str]:
    base = PORTALS[name]["base"]
    if name == "sabah":
        doc = f.get(base + "/ruya-tabirleri", name="index/ruya-tabirleri.html").text
        urls = [u for u in links(doc, base) if "/ruya-tabirleri/" in u]
        return list(dict.fromkeys(urls + turkuvaz_archives(f, base, "sabah.com.tr/ruya-tabirleri/")))
    if name == "takvim":
        doc = f.get(base + "/ruya-tabirleri", name="index/ruya-tabirleri.html").text
        urls = [u for u in links(doc, base) if "/ruya-tabirleri/20" in u]
        return list(dict.fromkeys(urls + turkuvaz_archives(f, base, "takvim.com.tr/ruya-tabirleri/20")))
    if name == "haberturk":
        doc = f.get(base + "/ruya-tabirleri", name="index/ruya-tabirleri.html").text
        return [u for u in links(doc, base) if re.match(r"https://www\.haberturk\.com/ruyada-", u)]
    if name == "haberler-com":
        doc = f.get(base + "/ruya-tabirleri/", name="index/ruya-tabirleri.html").text
        letters = [u for u in links(doc, base) if re.match(r"https://www\.haberler\.com/ruya-tabirleri/[^/]+/$", u)]
        urls = [u for u in links(doc, base) if u.endswith("-haberi/") and "ruya" in u]
        for lu in letters:
            try:
                d = f.get(lu, name=f"index/{lu.rstrip('/').rsplit('/', 1)[-1]}.html").text
            except Exception as e:  # noqa: BLE001
                print("letter fail", lu, e)
                continue
            urls += [u for u in links(d, base) if u.endswith("-haberi/") and "ruya" in u]
        return list(dict.fromkeys(urls))
    if name == "mynet":
        doc = f.get(base + "/trend/ruya-tabirleri", name="index/ruya-tabirleri.html").text
        letters = [u for u in links(doc, base) if re.match(r"https://www\.mynet\.com/trend/ruya-tabirleri/[^/]+$", u)]
        urls = [u for u in links(doc, base) if re.match(r"https://www\.mynet\.com/ruyada-", u)]
        for lu in letters:
            try:
                d = f.get(lu, name=f"index/{lu.rsplit('/', 1)[-1]}.html").text
            except Exception as e:  # noqa: BLE001
                print("letter fail", lu, e)
                continue
            urls += [u for u in links(d, base) if re.match(r"https://www\.mynet\.com/ruyada-", u)]
        return list(dict.fromkeys(urls))
    if name == "elele":
        doc = f.get(base + "/astroloji/ruya-tabirleri", name="index/ruya-tabirleri.html").text
        letters = [u for u in links(doc, base) if re.search(r"/astroloji/ruya-tabirleri/harf-[^/?]+$", u)]
        urls: list[str] = []
        for lu in letters:
            page = 1
            while page < 200:
                pu = lu if page == 1 else f"{lu}?sayfa={page}"
                try:
                    d = f.get(pu, name=f"index/{lu.rsplit('/', 1)[-1]}-{page}.html").text
                except Exception as e:  # noqa: BLE001
                    print("letter fail", pu, e)
                    break
                new = [u for u in links(d, base)
                       if re.search(r"/astroloji/ruya-tabirleri/(?!harf-)[^/?]+$", u) and u not in urls]
                if not new:
                    break
                urls += new
                page += 1
        return urls
    if name == "onedio":
        urls: list[str] = []
        t = f.get(base + "/siteMapEvergreen.xml", name="sitemaps/siteMapEvergreen.xml").text
        urls += [u for u in locs(t) if "/ruyada-" in u or "ruya-tabir" in u]
        idx = f.get(base + "/siteMapIndex.xml", name="sitemaps/siteMapIndex.xml").text
        for sm in locs(idx):
            m = re.search(r"/(\d{2})-(\d{4})\.xml\.gz$", sm)
            if not m or int(m.group(2)) < 2019:
                continue
            try:
                body = f.get(sm, save=False).content
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass
                hits = [u for u in locs(body.decode("utf-8", "replace")) if "/ruyada-" in u or "ruya-tabir" in u]
                urls += hits
                if hits:
                    print(sm, len(hits), flush=True)
            except Exception as e:  # noqa: BLE001
                print("sitemap fail", sm, e)
        return list(dict.fromkeys(urls))
    raise SystemExit(f"unknown portal {name}")


# ---------------------------------------------------------------- extraction

JUNK_HEAD = re.compile(r"(ilgili|benzer|ayrıca bak|okumaya devam|reklam|rüya tabiri arayın|a'dan z'ye|etiketler|haberin devamı|kaynak:)", re.I)
JUNK_PARA = re.compile(r"^(ilgili haber|ayrıca|bunlar da ilginizi|tıklayın|haberin devamı|kaynak:|foto(ğraf)?:)", re.I)


def extract_doc(name: str, doc: str, url: str) -> list[dict]:
    root = T.parse(doc)
    title = T.h1(root) or T.meta(doc, "og:title")
    block = None
    if name == "sabah":
        block = T.find(root, "div", "newsBox")
    elif name == "elele":
        block = T.find(root, "div", "news-content")
    elif name == "mynet":
        block = T.find(root, "div", "detail-content-inner")
    elif name == "haberturk":
        block = T.find(root, "div", "cms-container")
    block = block or T.main_block(root)
    if block is None:
        return []
    symbol = T.symbol_from_title(title)
    author = ""
    if name == "elele":
        m = re.search(r"([A-ZÇĞİÖŞÜ][\wçğıöşü]+(?: [A-ZÇĞİÖŞÜ][\wçğıöşü]+){1,2}), rüyada .{0,80}?yorumluyor", block.text())
        author = m.group(1) if m else ""
    rows = []
    info = PORTALS[name]
    for head, anchor, paras in T.sections(block):
        if head and JUNK_HEAD.search(head):
            continue
        paras = [p for p in paras if not JUNK_PARA.search(p)]
        if not paras:
            continue
        r = T.row(name, "turk-modern", symbol, head, "\n".join(paras), url,
                  ("#" + anchor) if anchor else (head or "giriş"), LIC, info["rights"], title=title)
        r["attributed_author"] = author
        rows.append(r)
    return rows


def crawl(name: str) -> None:
    info = PORTALS[name]
    f = Fetcher(Meta(source=name, license=LIC, rights_holder=info["rights"], tradition="turk-modern"), delay=1.5)
    urls = discover(name, f)
    print(name, "article urls:", len(urls), flush=True)
    (f.dir / "urls.txt").write_text("\n".join(urls), encoding="utf-8")
    for i, u in enumerate(urls):
        if f.seen(u):
            continue
        slug = re.sub(r"[^a-z0-9-]+", "-", u.split("://", 1)[1].split("/", 1)[-1].lower()).strip("-")[:150]
        try:
            f.get(u, name=f"articles/{slug}.html")
        except Blocked as e:
            print("BLOCKED", e, flush=True)
            break
        except Exception as e:  # noqa: BLE001
            with (f.dir / "errors.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"url": u, "error": str(e)[:300]}, ensure_ascii=False) + "\n")
        if i % 100 == 0:
            print(name, i, "/", len(urls), flush=True)


def extract(name: str) -> None:
    d = ROOT / name
    out = d / "entries.jsonl"
    if out.exists():
        out.unlink()
    rows: list[dict] = []
    n = 0
    seen_text: set[tuple[str, str]] = set()
    with (d / "manifest.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if not rec["path"].startswith("files/articles/"):
                continue
            n += 1
            doc = (d / rec["path"]).read_text(encoding="utf-8", errors="replace")
            for r in extract_doc(name, doc, rec["url"]):
                key = (r["condition"], r["meaning"][:200])
                if key in seen_text:
                    continue
                seen_text.add(key)
                rows.append(r)
    write_entries(name, rows)
    print(name, "articles:", n, "entries:", len(rows))


def probe_blocked() -> None:
    for name, url in BLOCKED_PROBES.items():
        f = Fetcher(Meta(source=name, license=LIC, tradition="turk-modern"), delay=1.0)
        try:
            f.get(url, save=False)
            print(name, "NOT blocked (unexpected)")
        except Blocked as e:
            print(name, "blocked:", e)
        except Exception as e:  # noqa: BLE001
            print(name, "error:", e)


if __name__ == "__main__":
    portal = sys.argv[1]
    if portal == "blocked":
        probe_blocked()
        raise SystemExit
    if len(sys.argv) < 3 or sys.argv[2] != "extract":
        crawl(portal)
    extract(portal)
