"""Wisdom Library (wisdomlib.org): English translations of Indian dream chapters.

Pages (robots.txt allows /…/book/…/d/doc*.html; search pages are disallowed and
not used):
- Kalpa Sūtra, tr. H. Jacobi 1884 (SBE 22; public domain): 14 great dreams.
- Suśruta Saṃhitā Sūtrasthāna 29, tr. K. L. Bhishagratna 1907 (public domain).
- Caraka Saṃhitā Indriyasthāna 5, Shree Gulabkunverba Ayurvedic Society 1949.
- Jātaka 77 Mahāsupina-jātaka, tr. R. Chalmers 1895 (Cowell ed.; public domain).
- Agni Purāṇa 229 svapnādhyāya, tr. N. Gangadharan 1954 (Motilal; copyrighted).
- Buddhacarita (Chinese recension), tr. C. Willemen, BDK 2009 (CC BY-NC-SA 3.0).
Each page: raw HTML in files/, paragraphs in texts.jsonl, symbol rows in
entries.jsonl (only where the text itself lists dream images with meanings).
"""

from __future__ import annotations

import html
import json
import re

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "wisdomlib"
BASE = "https://www.wisdomlib.org"
PAGES = [
    # (key, path, work, translator/edition, license, rights_holder, tradition)
    *[(f"kalpasutra-{i}", f"/jainism/book/kalpa-sutra/d/doc{424480 + i}.html",
       "Kalpa Sūtra (Bhadrabāhu)", "Hermann Jacobi 1884, SBE 22",
       "public domain (1884 translation)", "public domain", "jain") for i in range(0, 11)],
    ("sushruta-sutra-29", "/hinduism/book/sushruta-samhita-volume-1-sutrasthana/d/doc122928.html",
     "Suśruta Saṃhitā, Sūtrasthāna 29", "Kaviraj Kunja Lal Bhishagratna 1907",
     "public domain (1907 translation)", "public domain", "indian-ayurvedic"),
    ("charaka-indriya-5", "/hinduism/book/charaka-samhita-english/d/doc1083015.html",
     "Caraka Saṃhitā, Indriyasthāna 5", "Shree Gulabkunverba Ayurvedic Society 1949",
     "unclear: 1949 Indian edition (likely PD in India, US status unverified)",
     "Shree Gulabkunverba Ayurvedic Society / wisdomlib", "indian-ayurvedic"),
    ("jataka-77", "/buddhism/book/jataka-tales-english/d/doc80123.html",
     "Jātaka 77, Mahāsupina-jātaka", "Robert Chalmers 1895 (Cowell ed., vol. 1)",
     "public domain (1895 translation)", "public domain", "buddhist-pali"),
    ("agni-purana-229", "/hinduism/book/the-agni-purana/d/doc1083458.html",
     "Agni Purāṇa 229, svapnādhyāya", "N. Gangadharan 1954",
     "copyrighted (Motilal Banarsidass); research copy only", "Motilal Banarsidass", "indian-puranic"),
    ("buddhacarita-1", "/buddhism/book/buddhacarita/d/doc7700.html",
     "Buddhacarita (Chinese recension), Chapter I - Birth", "Charles Willemen, BDK English Tripiṭaka 2009",
     "CC BY-NC-SA 3.0 (BDK)", "Bukkyo Dendo Kyokai / BDK America", "buddhist-mahayana"),
]


def paragraphs(page: str) -> tuple[list[str], list[str]]:
    m = re.search(r'id="scontent"[^>]*>(.*?)(<section class="footnotes"|<div class="col-12 mb-3 chapter-dates")',
                  page, re.S)
    body = m.group(1) if m else ""
    notes = ""
    n = re.search(r'<section class="footnotes">(.*?)</section>', page, re.S)
    if n:
        notes = n.group(1)

    def clean(x: str) -> str:
        x = re.sub(r"<sup[^>]*>.*?</sup>", "", x, flags=re.S)
        x = re.sub(r"<[^>]+>", " ", x)
        return re.sub(r"\s+", " ", html.unescape(x)).strip()

    paras = [clean(p) for p in re.findall(r"<(?:p|h\d|blockquote)[^>]*>(.*?)</(?:p|h\d|blockquote)>", body, re.S)]
    fns = [clean(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", notes, re.S)]
    return [p for p in paras if p], [p for p in fns if p]


def base_row(meta: dict, url: str, locator: str) -> dict:
    return {"source": SOURCE, "tradition": meta["tradition"], "language": "en",
            "symbol_raw": "", "condition": "", "meaning": "", "polarity": "", "domain": "",
            "url": url, "locator": locator, "license": meta["license"],
            "rights_holder": meta["rights_holder"], "attributed_author": meta["work"],
            "translator": meta["translator"]}


def main() -> None:
    f = Fetcher(Meta(SOURCE, license="per page (see texts.jsonl)", rights_holder="per page",
                     tradition="indian"), delay=2.0)
    out = ROOT / SOURCE / "texts.jsonl"
    texts: dict[str, dict] = {}
    queue = list(PAGES)
    with out.open("w", encoding="utf-8") as fh:
        while queue:
            key, path, work, tr, lic, rh, trad = queue.pop(0)
            url = BASE + path
            try:
                local = ROOT / SOURCE / "files" / f"{key}.html"
                if f.seen(url) and local.exists():
                    page = local.read_text(encoding="utf-8")
                else:
                    page = f.get(url, name=f"{key}.html").text
            except Blocked as e:
                print("blocked", url, e)
                continue
            paras, notes = paragraphs(page)
            title = re.search(r"<title>(.*?)</title>", page, re.S)
            row = {"key": key, "url": url, "title": html.unescape(title.group(1).strip()) if title else "",
                   "work": work, "translator": tr, "license": lic, "rights_holder": rh,
                   "tradition": trad, "paragraphs": paras, "footnotes": notes}
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            texts[key] = row
            print(key, len(paras), "paras")

    rows = extract(texts)
    epath = ROOT / SOURCE / "entries.jsonl"
    if epath.exists():
        epath.unlink()
    write_entries(SOURCE, rows)
    print("entries:", len(rows))


def extract(texts: dict[str, dict]) -> list[dict]:
    return []


if __name__ == "__main__":
    main()
