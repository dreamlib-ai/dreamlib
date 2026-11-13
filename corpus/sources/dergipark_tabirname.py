"""Open-access Ottoman / Old Anatolian Turkish tabirname editions on DergiPark.

Fetches each article landing page and its PDF through the Fetcher, converts the
PDF to text with the system `pdftotext` (poppler, ships with Git for Windows),
and extracts conditional dream sentences from the transliterated text
("Eger düşinde ... görse, ... delâlet ider").

Usage (repo root):
    backend/.venv/Scripts/python -m corpus.sources.dergipark_tabirname [extract]
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys

from corpus.fetch import Blocked, Fetcher, Meta, ROOT, write_entries

SOURCE = "dergipark-tabirname"
BASE = "https://dergipark.org.tr"
META = Meta(source=SOURCE, license="makale bazında (landing page lisansı, çoğunlukla CC BY-NC)",
            rights_holder="makale yazarları / dergi", tradition="osmanli-tabirname")

# landing pages found via web search (DergiPark search itself is robots-disallowed)
ARTICLES = [
    "/tr/pub/iutded/article/1118495",      # Sıra Dışı Üç Rüya Tabirnâmesi (Bahadır 2022)
    "/tr/pub/soylemdergi/article/1111905",  # Rüya Tâbirnâmesi ... göstergebilimsel (Bayram 2022)
    "/tr/pub/belleten/article/946945",      # Eski Uygurca bir tabirname
    "/tr/pub/belleten/article/655123",      # Ahmed-i Dâî'nin Kitâbü't-ta'bîr tercümesi (Çebi)
    "/tr/pub/avrasyad/article/664182",      # British Museum'daki XVII. yy Türkçe ta'bir-nâme
    "/tr/pub/rumelide/article/1104154",     # Kâmilü't-Ta'bîr (Eski Oğuz Türkçesi)
    "/tr/pub/nesir/article/1741582",        # Şeyh Ali'nin Ta'bîrnâme'si
    "/tr/pub/akaded/article/1444029",       # Hacı Muhammed Mostârî'nin Tabîrnâmesi
    "/tr/pub/devdergisi/article/1303830",   # İbni Sîrîn'den yapılan tabirnameler ve tercümeleri
    "/tr/pub/akaded/issue/62203",           # Avanzâde Mehmet Süleyman, Muabbir (issue page, article link resolved)
]
EXTRA_FILES = ["/tr/download/article-file/4895322", "/tr/download/article-file/2377070"]


def meta_all(doc: str, name: str) -> list[str]:
    return [html.unescape(m) for m in re.findall(r'<meta name="%s" content="([^"]*)"' % re.escape(name), doc)]


def pdftotext() -> str | None:
    return shutil.which("pdftotext") or (r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"
                                         if shutil.which("git") else None)


def crawl() -> None:
    f = Fetcher(META, delay=2.0)
    info: list[dict] = []
    pages = list(ARTICLES)
    i = 0
    while i < len(pages):
        path = pages[i]
        i += 1
        url = BASE + path
        try:
            doc = f.get(url, name="pages/" + path.strip("/").replace("/", "_") + ".html").text
        except Blocked as e:
            print("BLOCKED", e)
            continue
        except Exception as e:  # noqa: BLE001
            print("fail", url, e)
            continue
        if "/issue/" in path:
            for href, title in re.findall(r'<a href="([^"]+/article/\d+)"[^>]*>\s*([^<]*)', doc):
                if re.search(r"tabir|ta.b[iî]r|muabbir", title, re.I):
                    p = re.sub(r"^https://dergipark\.org\.tr", "", href)
                    if p not in pages:
                        pages.append(p)
            continue
        lic = re.findall(r'(https?://creativecommons\.org/licenses/[^"\s]+)', doc)
        pdf = meta_all(doc, "citation_pdf_url") or [BASE + h for h in re.findall(r'href="(/tr/download/article-file/\d+)"', doc)]
        rec = {
            "page": url,
            "title": (meta_all(doc, "citation_title") or [""])[0],
            "authors": meta_all(doc, "citation_author"),
            "journal": (meta_all(doc, "citation_journal_title") or [""])[0],
            "date": (meta_all(doc, "citation_publication_date") or meta_all(doc, "citation_date") or [""])[0],
            "license": lic[0] if lic else "",
            "pdf": (BASE + pdf[0] if pdf[0].startswith("/") else pdf[0]) if pdf else "",
        }
        info.append(rec)
        print(rec["title"][:80], "|", rec["license"], "|", rec["pdf"])
    for extra in EXTRA_FILES:
        info.append({"page": "", "title": "", "authors": [], "journal": "", "date": "", "license": "", "pdf": BASE + extra})
    tool = pdftotext()
    for rec in info:
        if not rec["pdf"]:
            continue
        fid = rec["pdf"].rstrip("/").rsplit("/", 1)[-1]
        rec["file"] = f"files/pdf/{fid}.pdf"
        try:
            r = f.get(rec["pdf"], name=f"pdf/{fid}.pdf")
        except Blocked as e:
            print("BLOCKED", e)
            continue
        except Exception as e:  # noqa: BLE001
            print("pdf fail", rec["pdf"], e)
            continue
        if not rec["title"]:
            rec["content_type"] = r.headers.get("content-type", "")
        if tool:
            out = f.dir / "files" / "text" / f"{fid}.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([tool, "-enc", "UTF-8", str(f.dir / rec["file"]), str(out)], check=False)
            rec["text"] = f"files/text/{fid}.txt"
    (f.dir / "articles.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- extraction

START = re.compile(r"(?:(?<=[\s.;:])|^)((?:ve\s+|ammā\s+|amma\s+)?(?:eger|eğer|egerü|egerçi|ger)\s)", re.I)
SEE = re.compile(r"^(.{8,260}?\b(?:gör(?:se|ürse|mek|e|di|dügi|dügin)|düşinde|tüşinde|rü[\'’`]?yāda|rüyāsında|vāḳi[\'’`]asında)\w*[^,;]*?[,;]?)\s+(.{8,})$", re.I | re.S)


def norm(t: str) -> str:
    t = re.sub(r"-\n(?=\w)", "", t)          # hyphenation
    t = re.sub(r"\s*\n\s*", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def extract() -> None:
    d = ROOT / SOURCE
    out = d / "entries.jsonl"
    if out.exists():
        out.unlink()
    info = json.loads((d / "articles.json").read_text(encoding="utf-8"))
    rows = []
    for rec in info:
        if not rec.get("text"):
            continue
        p = d / rec["text"]
        if not p.exists():
            continue
        pages = p.read_text(encoding="utf-8", errors="replace").split("\f")
        for pno, page in enumerate(pages, 1):
            text = norm(page)
            starts = [m.start(1) for m in START.finditer(text)]
            for k, s in enumerate(starts):
                e = starts[k + 1] if k + 1 < len(starts) else len(text)
                sent = text[s:e].strip()
                dot = re.search(r"[.!]\s", sent[30:])
                if dot and k + 1 >= len(starts):
                    sent = sent[: 30 + dot.end()].strip()
                if len(sent) < 25 or len(sent) > 900:
                    continue
                m = SEE.match(sent)
                if not m:
                    continue
                cond, meaning = m.group(1).strip(" ,;"), m.group(2).strip()
                # need an interpretation verb, otherwise it is prose about dreams
                if not re.search(r"(delālet|delalet|alāmet|alamet|nişān|işāret|işaret|ta[\'’`]?bīr|tabir|yorıl|yorul|olur|ola|ide|ider|ėde|eyler|bulur|irişe|gelür|gele)", meaning, re.I):
                    continue
                rows.append({
                    "source": SOURCE, "tradition": META.tradition, "language": "tr-osm (transkripsiyon)",
                    "symbol_raw": "", "condition": cond, "meaning": meaning, "polarity": "", "domain": "",
                    "url": rec["page"] or rec["pdf"], "locator": f"pdf s. {pno}",
                    "license": rec.get("license", ""), "rights_holder": "; ".join(rec.get("authors", [])) + (f" / {rec['journal']}" if rec.get("journal") else ""),
                    "attributed_author": "", "work_title": rec.get("title", ""),
                })
    write_entries(SOURCE, rows)
    print("entries:", len(rows))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "extract":
        crawl()
    extract()
