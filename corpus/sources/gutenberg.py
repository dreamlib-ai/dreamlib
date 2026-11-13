"""Project Gutenberg: public-domain dream books.

Searches the official catalog CSV for dream / dream-interpretation / sleep /
fortune-telling titles in every language, downloads the plain text of each
through the shared Fetcher, then parses the alphabetical dream dictionaries
into entries.jsonl.

Run from repo root:  backend/.venv/Scripts/python -m corpus.sources.gutenberg
Re-parse only:       ... -m corpus.sources.gutenberg --parse-only
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "gutenberg"
LICENSE = "Public domain in the USA; Project Gutenberg License (strip PG trademark for commercial reuse)"
RIGHTS = "public domain (Project Gutenberg edition)"
CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
TXT_URL = "https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt"
BOOK_URL = "https://www.gutenberg.org/ebooks/{n}"

# Named in the task / research atlas; always included.
EXPLICIT = {926, 60045, 54774, 65367, 13137, 71045, 50450, 40739, 66048, 44917,
            53879, 61057, 53870, 55082, 52741, 77597, 35690, 35549, 27242}

SUBJECT_RE = re.compile(
    r"^(dreams?|dream interpretation|sleep|sleep disorders|sleepwalking|insomnia|nightmares|"
    r"fortune-telling.*|divination.*|omens|oneiromancy|visions)( --.*)?$",
    re.I,
)
FICTION_RE = re.compile(r"fiction|drama|poetry|juvenile|fairy tales|librettos", re.I)
TITLE_RE = re.compile(
    r"dream.?book|traumbuch|traumdeut|clef des songes|libro dei sogni|droomboek|drömbok|drømmebog|"
    r"unikirja|sonnik|сонник|sennik|snář|oneirocrit|onirocrit|tabirname|interpret\w* of dreams",
    re.I,
)


def select(catalog: Path) -> list[dict]:
    out = []
    with catalog.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Type"] != "Text":
                continue
            n = int(r["Text#"])
            subs = [s.strip() for s in r["Subjects"].split(";") if s.strip()]
            fiction = any(FICTION_RE.search(s) for s in subs)
            by_subject = any(SUBJECT_RE.match(s) for s in subs) and not fiction
            by_title = bool(TITLE_RE.search(r["Title"])) and not fiction
            if n in EXPLICIT or by_subject or by_title:
                out.append({
                    "id": n,
                    "title": " ".join(r["Title"].split()),
                    "language": r["Language"],
                    "authors": r["Authors"],
                    "subjects": subs,
                    "issued": r["Issued"],
                    "locc": r["LoCC"],
                    "why": "explicit" if n in EXPLICIT else ("subject" if by_subject else "title"),
                })
    return out


def download(f: Fetcher, items: list[dict]) -> None:
    for it in items:
        url = TXT_URL.format(n=it["id"])
        it["url"] = url
        it["file"] = f"files/pg{it['id']}.txt"
        if f.seen(url):
            continue
        try:
            f.get(url, name=f"pg{it['id']}.txt")
            print("ok", it["id"], it["title"][:60])
        except Blocked as e:
            it["blocked"] = str(e)
            print("blocked", it["id"], e)
        except Exception as e:  # 404 etc.
            it["error"] = repr(e)
            print("error", it["id"], e)


# --------------------------------------------------------------------------
# Dictionary parsing (also imported by internet_archive.py for OCR text).
#
# mode "head":  one row per headword; body = text until the next headword.
# mode "multi": headword on its own line, each following paragraph = one row
#               (Miller); the leading "To dream ..." clause becomes `condition`.
# mode "sent":  no headwords; each "To dream ..." sentence = one row, the
#               dream clause goes to symbol_raw.
# `meaning` is always the source text itself; polarity/domain stay empty.
# --------------------------------------------------------------------------

PG_END = "*** END OF THE PROJECT GUTENBERG"
VERBS_EN = (r"denotes?|foretells?|signif(?:y|ies)|portends?|betokens?|indicates?|forebodes?|"
            r"foreshadows?|predicts?|presages?|prognosticates?|warns?|means?|implies|imports?|shows?|"
            r"is (?:a |an )?(?:certain |sure |good |bad |lucky |unlucky |very )*(?:sign|omen|token)|"
            r"foreshews|promises|declares|augurs?")
COND_RE = re.compile(rf"^(.{{3,220}}?),?\s+(?:it\s+)?(?:{VERBS_EN})\b", re.I | re.S)

SPECS: dict[int, dict] = {
    926: dict(mode="multi", lang="en", tradition="western-folk (American, 1901)",
              author="Gustavus Hindman Miller", start="\n_Abandon_.", end="\nINDEX\n",
              head=r"\n\n_([^_\n]{1,60})_\.(?:\[\d+\])?[ \t]*\n"),
    60045: dict(mode="head", lang="en", tradition="western-folk (American dream-book)", author="Felix Fontaine",
                start="A LIST OF DREAMS, WITH THEIR TRUE INTERPRETATION",
                end="LIST OF DREAMS, WITHOUT INTERPRETATIONS",
                head=r"\n\n([A-Z][A-Z'&,\- —]{0,40}[A-Z])\.\s"),
    54774: dict(mode="head", lang="en", tradition="western-folk (American dream-book)", author="Astra Cielo",
                start="\n      _Abandoned_", end="THE LANGUAGE OF FLOWERS",
                head=r"\n\n\s*_([^_\n]{1,60})_\s*—"),
    65367: dict(mode="head", lang="en", tradition="western-folk (English/American chapbook)", author="",
                start="\nAbuse.--", end=PG_END,
                head=r"\n\n([A-Z][A-Za-z' ,\-]{1,40})\.--"),
    53879: dict(mode="head", lang="en", tradition="western-folk (American dream-book)", author="A. H. Noe",
                start="=A", end="\nPHYSIOGNOMY.",
                head=r"=([^=\n]{1,60}?)\.?=\s*--"),
    50450: dict(mode="head", lang="sv", tradition="western-folk (Swedish drömbok, 19th c.)", author="Per Gustaf Berg (ed.)",
                start="\n#Accacia.#", end="\nNoteringar:",
                head=r"\n\n#([^#\n]{1,60}?)\.?#", keep_head=True),
    55082: dict(mode="head", lang="en", tradition="western-folk (British book of luck)", author="",
                start="\nDREAMS--WHAT THEY MEAN\n", end="\nTEACUP FORTUNETELLING",
                head=r"\n\n_([^_\n]{1,60}?)\.?_\.?--"),
    27242: dict(mode="head", lang="pt", tradition="western-folk (Portuguese livro dos sonhos)", author="Bento Serrano",
                start="\n_Abandonado_", end="\nTABELLA dos dias",
                head=r"\n\n_([^_\n]{1,60}?)_", keep_head=True),
    71045: dict(mode="sent", lang="en", tradition="western-folk (English chapbook)", author="",
                start="_DREAMS INTERPRETED._", end="AND THEIR PROGNOSTICATION."),
    77597: dict(mode="sent", lang="en", tradition="western-folk (American signs and omens)", author="Astra Cielo",
                start="*** START OF THE PROJECT GUTENBERG", end=PG_END),
    35690: dict(mode="sent", lang="en", tradition="south-indian folk (colonial ethnography)", author="Edgar Thurston",
                start="*** START OF THE PROJECT GUTENBERG", end=PG_END),
}

SENT_RE = re.compile(r"(?:(?<=^)|(?<=[.;!?\]]\s)|(?<=\n))(?:If\s+(?:a|an|one|you|he|she)\s+[^.;]{0,40}?)?"
                     r"(To dream[^.]{5,400}?\.)", re.S)


def _clean(s: str) -> str:
    s = re.sub(r"\[\d+\]", "", s)
    s = re.sub(r"\[Illustration[^\]]*\]", "", s)
    return " ".join(s.split()).strip()


def _section(text: str, spec: dict) -> tuple[str, int]:
    text = text.replace("\r\n", "\n")
    start = -1
    pos = 0
    for _ in range(spec.get("nth_start", 0) + 1):
        start = text.find(spec["start"], pos)
        if start < 0:
            return "", 0
        pos = start + len(spec["start"])
    end = text.find(spec["end"], pos) if spec.get("end") else -1
    sec = text[start:end if end > 0 else len(text)]
    line0 = text.count("\n", 0, start) + 1
    return "\n\n" + sec, line0


def _row(spec: dict, symbol: str, meaning: str, condition: str, locator: str) -> dict:
    return {
        "tradition": spec.get("tradition", ""), "language": spec.get("lang", ""),
        "symbol_raw": symbol, "condition": condition, "meaning": meaning,
        "polarity": "", "domain": "", "locator": locator,
        "attributed_author": spec.get("author", ""),
    }


def parse_book(text: str, spec: dict) -> list[dict]:
    sec, line0 = _section(text, spec)
    if not sec:
        return []
    rows: list[dict] = []
    if spec["mode"] == "sent":
        for m in SENT_RE.finditer(sec):
            sent = _clean(m.group(0))
            clause = COND_RE.match(_clean(m.group(1)))
            line = line0 + sec.count("\n", 0, m.start()) - 2
            rows.append(_row(spec, clause.group(1) if clause else "", sent, "", f"line {line}"))
        return rows
    heads = list(re.finditer(spec["head"], sec))
    for i, m in enumerate(heads):
        body = sec[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(sec)]
        sym = _clean(m.group(1)).strip(" .,:;")
        line = line0 + sec.count("\n", 0, m.start()) - 1
        if not sym or len(sym) > 60:
            continue
        if spec["mode"] == "multi":
            for k, para in enumerate(p for p in re.split(r"\n\s*\n", body) if p.strip()):
                if re.match(r"\s*\[\d+\]", para) or para.strip().startswith("{illust"):
                    continue  # footnote / illustration caption
                txt = _clean(para)
                if len(txt) < 12:
                    continue
                cm = COND_RE.match(txt)
                rows.append(_row(spec, sym, txt, cm.group(1).strip() if cm else "", f"line {line}, ¶{k + 1}"))
        else:
            txt = _clean(body)
            if spec.get("keep_head"):
                txt = _clean(sec[m.start(): m.end()] + body).replace("#", "")
            if len(txt) < 3:
                continue
            rows.append(_row(spec, sym, txt, "", f"line {line}"))
    return rows


# Generic heuristic for OCR'd dictionaries (Internet Archive). A paragraph is an
# entry when it starts with a short headword followed by punctuation and its body
# contains a dream/omen keyword of the book's language. Books where such
# paragraphs are rare are treated as non-dictionaries and yield nothing.
KEYWORDS = {
    "en": r"dream|signif|denot|foretel|portend|betoken|omen|forebod|indicat",
    "fr": r"songe|rêve|reve|signifie|présage|presage|annonce|dénote|denote|marque",
    "de": r"träum|traum|bedeutet|zeigt an|verkündet|verkundet|deutet",
    "it": r"sogn|significa|denota|annunzia|annuncia|presagio",
    "es": r"soñar|sonar|sueño|significa|anuncia|presagio|denota",
    "pt": r"sonh|significa|anuncia|presagio",
    "nl": r"droom|beteekent|betekent|voorspelt",
    "sv": r"dröm|betyder|bebådar",
    "ru": r"сни|видеть|означает|предвещает|знак",
    "la": r"somni|significat|portendit",
}
LANG_ALIASES = {"eng": "en", "english": "en", "fre": "fr", "fra": "fr", "french": "fr", "ger": "de", "deu": "de",
                "german": "de", "ita": "it", "italian": "it", "spa": "es", "spanish": "es", "por": "pt",
                "portuguese": "pt", "dut": "nl", "nld": "nl", "dutch": "nl", "swe": "sv", "swedish": "sv",
                "rus": "ru", "russian": "ru", "lat": "la", "latin": "la"}
GEN_HEAD = re.compile(r"^([A-ZÀ-ÝА-Я][A-Za-zÀ-ÿА-яЁё'’\- ]{1,30}?)\s*(?:[.,:;]\s*[—–-]{0,2}|[—–]|--)\s*(\S.{10,1500})$", re.S)


def lang_code(lang: str) -> str:
    for tok in re.split(r"[\s,;/]+", lang.lower()):
        if tok in KEYWORDS:
            return tok
        if tok in LANG_ALIASES:
            return LANG_ALIASES[tok]
    return "en"


def parse_generic(text: str, lang: str, min_rows: int = 30, min_ratio: float = 0.12) -> list[dict]:
    code = lang_code(lang)
    kw = re.compile(KEYWORDS[code], re.I)
    paras = [p for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]
    rows = []
    for i, p in enumerate(paras):
        txt = " ".join(p.split())
        m = GEN_HEAD.match(txt)
        if not m or not kw.search(m.group(2)):
            continue
        sym = m.group(1).strip()
        if len(sym.split()) > 4 or sym.lower() in {"chapter", "the", "a", "an", "fig", "plate", "page", "note"}:
            continue
        rows.append({"tradition": "western-folk (OCR dream-book)", "language": code, "symbol_raw": sym,
                     "condition": "", "meaning": txt, "polarity": "", "domain": "",
                     "locator": f"djvu.txt ¶{i + 1} (OCR)"})
    if code == "en" and len(rows) < min_rows:
        sents = [m.group(0) for m in SENT_RE.finditer(text)]
        if len(sents) >= min_rows:
            rows = []
            for s in sents:
                s = " ".join(s.split())
                cm = COND_RE.match(s)
                rows.append({"tradition": "western-folk (OCR dream-book)", "language": code,
                             "symbol_raw": cm.group(1) if cm else "", "condition": "", "meaning": s,
                             "polarity": "", "domain": "", "locator": "djvu.txt sentence (OCR)"})
            return rows
    if len(rows) < min_rows or len(rows) / max(len(paras), 1) < min_ratio:
        return []
    return rows


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parse_only = "--parse-only" in sys.argv
    base = ROOT / SOURCE
    meta = Meta(source=SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition="")
    f = Fetcher(meta, delay=2.0)
    catalog = base / "files" / "pg_catalog.csv"
    if not parse_only:
        if not f.seen(CATALOG_URL):
            f.get(CATALOG_URL, name="pg_catalog.csv")
    items = select(catalog)
    if not parse_only:
        download(f, items)
        with (base / "items.jsonl").open("w", encoding="utf-8") as out:
            for it in items:
                out.write(json.dumps(it, ensure_ascii=False) + "\n")
    else:
        items = [json.loads(l) for l in (base / "items.jsonl").open(encoding="utf-8")]

    entries_path = base / "entries.jsonl"
    if entries_path.exists():
        entries_path.unlink()
    total = 0
    counts = {}
    for it in items:
        spec = SPECS.get(it["id"])
        path = base / it.get("file", "")
        if not spec or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rows = parse_book(text, spec)
        for row in rows:
            row.update({
                "source": SOURCE,
                "url": BOOK_URL.format(n=it["id"]),
                "license": LICENSE,
                "rights_holder": RIGHTS,
            })
            row["locator"] = f"pg{it['id']}; " + row.get("locator", "")
        write_entries(SOURCE, rows)
        counts[it["id"]] = len(rows)
        total += len(rows)
    (base / "entry_counts.json").write_text(json.dumps(counts, indent=1), encoding="utf-8")
    print("entries", total, counts)


if __name__ == "__main__":
    main()
