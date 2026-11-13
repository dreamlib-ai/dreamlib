"""Japanese reference/public-domain slice: ja.wikipedia.org /wiki/ pages, Aozora Bunko 夢十夜, Osaka Univ. OUKA 夢占逸旨 papers.

- ja.wikipedia: /wiki/ HTML allowed by robots (API is not). CC BY-SA 4.0.
- Aozora Bunko: 夏目漱石 夢十夜 (author d. 1916, public domain; Aozora volunteer input by 野口英司). One row per 夜.
- OUKA (ir.library.osaka-u.ac.jp): 清水洋子 陳士元『夢占逸旨』内篇訳注 series and 上野洋子 papers, open access
  but copyright with authors, no CC licence stated, and the site forbids mass downloading: we fetch only this short
  fixed list of PDFs, raw only (no PDF parser in the venv, so no entries.jsonl rows).
Run: backend/.venv/Scripts/python -m corpus.sources.jp_reference
"""
from __future__ import annotations

import html
import re
from urllib.parse import quote

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries
from corpus.sources.krjp_common import generic_rows, get_text, run

WIKI = ["夢占い", "初夢", "夢", "夢判断", "正夢", "予知夢", "悪夢", "明晰夢", "夢違え", "一富士二鷹三茄子", "夢解き", "周公解夢"]
OUKA = ["11517/mrp_038-065.pdf", "58049/cks_054_056.pdf", "58722/cks_060_107.pdf", "58719/cks_056_197.pdf",
        "58701/cks_055_166.pdf", "61247/cks_047_060.pdf", "61196/cks_048_127.pdf", "60923/cks_051_001.pdf"]


def wiki() -> None:
    src = "ja-wikipedia-yume"
    f = Fetcher(Meta(src, "CC BY-SA 4.0", "Wikipedia contributors", "Japonya ansiklopedik"), delay=2.0)
    base = {"source": src, "tradition": "Japonya ansiklopedik (Wikipedia)", "language": "ja", "domain": "ansiklopedi",
            "license": "CC BY-SA 4.0", "rights_holder": "Wikipedia contributors", "attributed_author": ""}
    urls = [f"https://ja.wikipedia.org/wiki/{quote(t)}" for t in WIKI]
    run(f, src, urls, lambda p, u: generic_rows(p, u, base, lambda s: s, min_len=30, block_cls="mw-parser-output"), 100)


def aozora() -> None:
    src = "aozora-yume"
    lic = "Public domain (author d. 1916); Aozora Bunko terms of use"
    f = Fetcher(Meta(src, lic, "青空文庫 (input: 野口英司)", "Japonya edebi"), delay=2.0)
    url = "https://www.aozora.gr.jp/cards/000148/files/799_14972.html"
    try:
        f.get(url, name="799_14972.html")
    except Blocked as e:
        print("blocked", e)
        return
    raw = (f.dir / "files" / "799_14972.html").read_bytes().decode("cp932", errors="replace")
    body = raw.split('<div class="main_text">', 1)[-1]
    parts = re.split(r'<h4 class="naka-midashi[^"]*"[^>]*>(.*?)</h4>', body)
    rows = []
    for i in range(1, len(parts) - 1, 2):
        head = re.sub(r"<[^>]+>", "", parts[i]).strip()
        txt = re.sub(r"<rp>.*?</rp>|<rt>.*?</rt>", "", parts[i + 1], flags=re.S)
        txt = html.unescape(re.sub(r"<br ?/?>", "\n", re.sub(r"</?(?:ruby|rb|div|span|a)[^>]*>", "", txt)))
        txt = re.sub(r"<[^>]+>", "", txt).strip()
        rows.append({"source": src, "tradition": "Japonya edebi (rüya anlatısı, tabir sözlüğü değil)", "language": "ja",
                     "symbol_raw": f"夢十夜 {head}", "condition": "", "meaning": txt, "polarity": "bilinmiyor",
                     "domain": "edebiyat", "url": url, "locator": head, "license": lic,
                     "rights_holder": "青空文庫", "attributed_author": "夏目漱石"})
    p = ROOT / src / "entries.jsonl"
    p.unlink(missing_ok=True)
    write_entries(src, rows)
    print("aozora rows", len(rows))


def ouka() -> None:
    src = "osaka-ouka-yumeurani"
    lic = "Open access, no CC licence stated; copyright with authors (OUKA rights page); mass download forbidden"
    f = Fetcher(Meta(src, lic, "大阪大学学術情報庫 OUKA / authors 清水洋子, 上野洋子", "Çin/Japonya akademik"), delay=5.0)
    for i in OUKA:
        u = f"https://ir.library.osaka-u.ac.jp/repo/ouka/all/{i}"
        try:
            r = f.get(u, name=i.split("/")[1])
            print("ok", i, len(r.content))
        except Blocked as e:
            print("blocked", e)
        except Exception as e:  # noqa: BLE001
            print("error", i, repr(e)[:100])


if __name__ == "__main__":
    wiki()
    aozora()
    ouka()
