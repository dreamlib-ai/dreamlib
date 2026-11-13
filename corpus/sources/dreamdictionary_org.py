"""dreamdictionary.org: A-Z dream dictionary (modern English, WordPress, commercial).

Only the 26 letter pages (/a/ ... /z/) are fetched; they carry short entries
inline as <div class="interpretation"><p><strong>Symbol</strong></p><p>text</p>.
Search/feed paths are disallowed and never requested.
"""

from __future__ import annotations

import html
import json
import re
import string

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "dreamdictionary.org"
BASE = "https://www.dreamdictionary.org"
META = Meta(
    source=SOURCE,
    license="copyrighted, all rights reserved (no reuse licence)",
    rights_holder="DreamDictionary.org operator (legal name not confirmed)",
    tradition="modern-western-popular",
)


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()


def main() -> None:
    f = Fetcher(META, delay=2.0)
    seen: dict[str, str] = {}
    if f.manifest.exists():
        for line in f.manifest.open(encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                seen[r["url"]] = r["path"]
    out = ROOT / SOURCE / "entries.jsonl"
    if out.exists():
        out.unlink()
    rows: list[dict] = []
    for url_tail in ["/submit/"] + [f"/{c}/" for c in string.ascii_lowercase]:
        url = BASE + url_tail
        name = "letter_" + url_tail.strip("/") + ".html"
        try:
            if url in seen:
                body = (f.dir / seen[url]).read_text(encoding="utf-8", errors="replace")
            else:
                body = f.get(url, name=name).text
        except (Blocked, Exception) as e:
            print("ERR", url, str(e)[:100], flush=True)
            continue
        if url_tail == "/submit/":
            continue
        n = 0
        for m in re.finditer(r'(?is)<div class="interpretation">(.*?)</div>\s*(?=<div class="interpretation">|</div>|$)', body):
            blk = m.group(1)
            sm = re.search(r"(?is)<p>\s*<strong>(.*?)</strong>\s*</p>", blk)
            if not sm:
                continue
            sym = clean(sm.group(1))
            paras = [clean(p) for p in re.findall(r"(?is)<p>(.*?)</p>", blk[sm.end():])]
            for p in paras:
                if len(p) < 15:
                    continue
                n += 1
                rows.append({
                    "source": SOURCE, "tradition": META.tradition, "language": "en",
                    "symbol_raw": sym, "condition": "", "meaning": p, "polarity": "bilinmiyor",
                    "domain": "", "url": url, "locator": f"{url_tail.strip('/')}#{sym}",
                    "license": META.license, "rights_holder": META.rights_holder,
                    "attributed_author": "",
                })
        print(url_tail, n, flush=True)
    write_entries(SOURCE, rows)
    print("entries", len(rows), "symbols", len({r["symbol_raw"] for r in rows}))


if __name__ == "__main__":
    main()
