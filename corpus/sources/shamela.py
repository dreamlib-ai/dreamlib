"""Shamela (shamela.ws) dream books: landing card + every page (ajax pageContent JSON).

shamela.ws has no robots.txt (404 on 2026-10-25), so fetching is allowed; we go
slowly (2 s/request). Book ids come from a scan of all 40 categories for
ta'bir/ru'ya/ahlam/manam titles plus Ibn Shahin (9968, not listed in a category).
Parse: headwords are <span class="c2">(X)</span> at paragraph start; otherwise
the page's TOC title names the symbol (same cleaning as the OpenITI parser).

Run: backend/.venv/Scripts/python -m corpus.sources.shamela [download|parse]
"""

from __future__ import annotations

import html
import json
import re
import sys

import httpx

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries
from corpus.sources.openiti_parse import Book, headword, heading_symbol

SOURCE = "shamela"
DIR = ROOT / SOURCE
LICENSE = "no explicit license (free waqf library); classical text public domain, printed edition rights with publisher"
RIGHTS = "al-Maktaba al-Shamela (shamela.ws) digitisation; edition publisher per book card"
BOOKS = {
    "1217": ("تعطير الأنام في تعبير المنام", "عبد الغني النابلسي (Nabulusi)", "islamic-classical"),
    "21615": ("منتخب الكلام في تفسير الأحلام", "ابن سيرين (Ibn Sirin) [attributed]", "islamic-classical"),
    "9968": ("الإشارات في علم العبارات", "خليل بن شاهين الظاهري (Ibn Shahin)", "islamic-classical"),
    "10696": ("تعبير الرؤيا", "ابن غنام (Ibn Ghannam)", "islamic-classical"),
    "10703": ("البدر المنير في علم التعبير", "شهاب الدين المقدسي النابلسي", "islamic-classical"),
    "10698": ("الإشارة إلى علم العبارة", "السالمي (Salimi)", "islamic-classical"),
    "10652": ("تنبيه الأفهام بتأويل الأحلام", "الإحسائي الحنفي (Ihsai)", "islamic-classical"),
    "13070": ("المنامات", "ابن أبي الدنيا (Ibn Abi al-Dunya)", "islamic-classical"),
    "20824": ("كتاب الرؤيا", "", "islamic-classical"),
    "230": ("موسوعة تفسير الأحلام (ترجمة)", "Gustavus Hindman Miller; çev. هدى موسى", "western-modern (Arabic translation)"),
}
NARRATIVE = {"13070", "20824"}  # dream narratives / hadith, no symbol structure
PAGE = "https://shamela.ws/ajax/pageContent/{bid}/{pid}"


def download() -> None:
    f = Fetcher(Meta(SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition="islamic-classical"), delay=2.0)
    for bid in BOOKS:
        try:
            f.get(f"https://shamela.ws/book/{bid}", name=f"{bid}/card.html")
        except (Blocked, httpx.HTTPError) as e:
            print("card failed", bid, e)
            continue
        pid, n = "1", 0
        while pid:
            url = PAGE.format(bid=bid, pid=pid)
            path = DIR / "files" / bid / "pages" / f"{int(pid):05d}.json"
            try:
                if f.seen(url) and path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data = f.get(url, name=f"{bid}/pages/{int(pid):05d}.json").json()
            except Blocked as e:
                print("blocked", e)
                break
            except (httpx.HTTPError, ValueError) as e:
                print("page failed", url, e)
                break
            n += 1
            nxt = str(data.get("nextId") or "")
            pid = nxt if nxt and nxt != pid else ""
        print(bid, "pages", n, flush=True)


def paragraphs(nass: str) -> list[tuple[str, bool]]:
    """(text, starts_with_headword_span) per <p>."""
    out = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", nass, flags=re.S):
        p = re.sub(r'<a href="#[^"]*" class="btn_tag.*?</a>', "", p, flags=re.S)
        hw = bool(re.match(r'^\s*(<span[^>]*anchor[^>]*></span>)?\s*-?\s*<span class="c2">', p))
        heading = bool(re.match(r'^\s*(<span[^>]*anchor[^>]*></span>)?\s*<span class="c4">', p))
        text = html.unescape(re.sub(r"<[^>]+>", "", p))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append((("#H " if heading else "") + text, hw))
    return out


def parse() -> None:
    target = DIR / "entries.jsonl"
    if target.exists():
        target.unlink()
    book_cfg = Book(version="", paren=True)
    total = 0
    for bid, (title, author, tradition) in BOOKS.items():
        if bid in NARRATIVE:
            continue
        pages = sorted((DIR / "files" / bid / "pages").glob("*.json"))
        rows: list[dict] = []
        cur: dict | None = None
        last_title = None

        def flush() -> None:
            nonlocal cur
            if cur and len(cur["meaning"]) >= 8:
                cur["meaning"] = re.sub(r"\s+", " ", cur["meaning"]).strip()
                rows.append(cur)
            cur = None

        def new(sym: str, text: str, d: dict, pid: str) -> dict:
            return {
                "source": SOURCE, "tradition": tradition, "language": "ar", "symbol_raw": sym,
                "condition": "", "meaning": text, "polarity": "", "domain": "",
                "url": f"https://shamela.ws/book/{bid}/{pid}",
                "locator": f"shamela {bid} | {d.get('title') or ''} | ص{d.get('pageNum') or ''}",
                "license": LICENSE if bid != "230" else "copyrighted Arabic translation (1990), not cleared",
                "rights_holder": RIGHTS if bid != "230" else "translator Huda Musa / publisher (unknown); Shamela",
                "attributed_author": author, "work": title,
            }

        for path in pages:
            d = json.loads(path.read_text(encoding="utf-8"))
            pid = str(d.get("pageId") or int(path.stem))
            t = (d.get("title") or "").strip()
            sym, intro = heading_symbol(t) if t else (None, False)
            if t != last_title:
                if cur and not cur.get("_hw"):
                    flush()
                last_title = t
            for text, hwspan in paragraphs(d.get("nass") or ""):
                if text.startswith("#H "):
                    flush()
                    continue
                if intro:
                    continue
                hw = headword(text, book_cfg) if hwspan or text.startswith(("(", "- (")) else None
                if hw:
                    flush()
                    cur = new(hw[0], hw[1], d, pid)
                    cur["_hw"] = True
                elif cur is not None and (cur.get("_hw") or len(cur["meaning"]) < 3000):
                    cur["meaning"] += " " + text
                elif sym:
                    flush()
                    cur = new(sym, text, d, pid)
        flush()
        for r in rows:
            r.pop("_hw", None)
        write_entries(SOURCE, rows)
        total += len(rows)
        print(bid, title, len(rows))
    print("total", total)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("download", "all"):
        download()
    if step in ("parse", "all"):
        parse()
