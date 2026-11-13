"""Parse downloaded OpenITI dream books into symbol -> meaning rows.

One version per work is parsed (the best structured one); the other versions
stay as raw files. Structure cues used, per book:
  - paragraph headwords "(X) …" / "- (X) …" (Nabulsi, Ibn Sirin, Ihsai),
  - "X: …" headwords inside letter chapters (Ibn Ghannam),
  - "[n] X - …" numbered headwords (al-Badr al-Munir),
  - headings that name a symbol ("فصل في رؤيا الشمس", "عط - في رؤية الطرفاء",
    Persian "زحل") for Ibn Shahin, Qadiri, Razi, Hunayn, Salimi, Ihsai.
`meaning` is the source text itself; condition/polarity/domain stay empty.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from corpus.fetch import ROOT, write_entries

SOURCE = "openiti"
DIR = ROOT / SOURCE
FILES = DIR / "files"
LICENSE = "CC BY-NC-SA 4.0 (OpenITI release, per Zenodo); classical text public domain"
RIGHTS = "OpenITI / KITAB (AKU-ISMC, Univ. Vienna, Univ. Maryland); edition per version yml"
RAW = "https://raw.githubusercontent.com/OpenITI/{repo}/master/{path}"


@dataclass
class Book:
    version: str  # file name of the parsed version
    heading_mode: str = "merge"  # merge: one entry per symbol heading; split: one per paragraph
    paren: bool = True
    colon: bool = False
    numbered: bool = False
    tradition: str = "islamic-classical"
    language: str = "ar"
    fi_headings: bool = False  # OCR text: only headings with "في" name a symbol, others are noise


PARSE = {
    "1143CabdGhaniNabulusi.TactirAnam": Book("1143CabdGhaniNabulusi.TactirAnam.Shamela0001217-ara1"),
    "0110IbnSirin.MuntakhabKalamFiTafsirAhlam": Book(
        "0110IbnSirin.MuntakhabKalamFiTafsirAhlam.Shamela0021615-ara1", heading_mode="split"
    ),
    "0873IbnShahinZahiri.Isharat": Book("0873IbnShahinZahiri.Isharat.Shamela0009968-ara1"),
    "0693IbnGhannam.TacbirRuya": Book("0693IbnGhannam.TacbirRuya.Shamela0010696-ara1", colon=True, heading_mode="split"),
    "0697AbuCabbasShihabDinNabulusi.QawacidTafsirAhlam": Book(
        "0697AbuCabbasShihabDinNabulusi.QawacidTafsirAhlam.Shamela0010703-ara1", numbered=True, heading_mode="split"
    ),
    "0800IbnAhmadAbuCabdAllahSalimi.IsharaIlaCilmCibara": Book(
        "0800IbnAhmadAbuCabdAllahSalimi.IsharaIlaCilmCibara.Shamela0010698-ara1"
    ),
    "1270IbnMuhammadIhsaiHanafi.TanbihAfham": Book("1270IbnMuhammadIhsaiHanafi.TanbihAfham.Shamela0010652-ara1"),
    "0410NasrIbnYacqub.QadiriFiTacbir": Book("0410NasrIbnYacqub.QadiriFiTacbir.AOCP2023090635Vols-ara1"),
    "0606FakhrDinRazi.TahbirCilmTacbir": Book(
        "0606FakhrDinRazi.TahbirCilmTacbir.AOCP202502141224-per1", paren=False, language="fa"
    ),
    "0259HunaynIbnIshaq.TacbirRuya": Book(
        "0259HunaynIbnIshaq.TacbirRuya.AOCP2023090634-ara1", paren=False, fi_headings=True, tradition="greco-arabic (Artemidorus)"
    ),
}

PAGE = re.compile(r"PageV(\d+)P(\d+)")
MS = re.compile(r"\bms\d+\b")
STOP = re.compile(
    r"^(و|ف)?(قد|وقد|من رأى|من رأي|ومن رأى|قال|قالت|حكي|حكى|روى|روي|اعلم|أخبرنا|اخبرنا|حدثنا|حدثني|فصل|قيل|مثاله|مثال|ومما|مما|"
    r"أما|اما|كقوله|لقوله|قوله|عن|بسم الله|الحمد لله|أي|يعني|انظر|المقالة|كما|لأن|لان|إن|ان|إذا|اذا|ثم|وهو|وهي|هو|هي|"
    r"أرطاميدورس|ارطاميدورس|دانيال|الكرماني|جعفر|ابن سيرين|المصنف|قال المصنف|الشاعر|تنبيه|فائدة|خاتمة|تتمة|مسألة|"
    r"أخرجه|رواه|ح|صح|ص|ع|انتهى)\b"
)
STRUCT = re.compile(
    r"^(ال)?(باب|فصل|الفصل|المقدمة|مقدمة|تقدمة|خاتمة|الخاتمة|تتمة|بسم الله|الحمد لله|حكاية|فهرست|قسم|المقالة)"
)
INTRO = re.compile(r"(مقدمة|المقدمة|تقدمة|خاتمة|بسم الله|الحمد لله|فهرست|فصول الكتاب|اللهم)")
ORDINAL_ONLY = re.compile(
    r"^(ال)?(باب|فصل|الفصل|الباب|فص|قسم|المقالة|مقالة)\s*(حرف\s*)?\S{0,12}(\s+(عشر|والعشرون|والثلاثون|والأربعون|والخمسون|"
    r"و\S+))?[\s.:]*$"
)
LETTER_BAB = re.compile(r"^باب\s+(حرف\s+)?\S{1,8}\.?$")


def read_version(path: Path) -> list[tuple[str, str, str]]:
    """Return ('h'|'p', text, page) units from an OpenITI mARkdown file."""
    units: list[list[str]] = []
    page = ""
    in_header = True
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if in_header:
            if line.startswith("#META#Header#End"):
                in_header = False
            continue
        m = PAGE.search(line)
        if m:
            vol, pg = m.groups()
            line = PAGE.sub("", line)
        if "![image" in line:
            line = ""
        stripped = line.strip()
        if stripped.startswith("### "):
            text = re.sub(r"^###\s*(\||\$)+\s*", "", stripped)
            units.append(["h", text, page])
        elif stripped.startswith("~~") or stripped.startswith("# ~~"):
            text = re.sub(r"^(#\s*)?~~", "", stripped)
            if units and units[-1][0] == "p":
                units[-1][1] += " " + text
            elif text.strip():
                units.append(["p", text, page])
        elif stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                units.append(["p", text, page])
        elif stripped:
            if units and units[-1][0] == "p":
                units[-1][1] += " " + stripped
            else:
                units.append(["p", stripped, page])
        if m:
            page = f"V{vol}P{pg}"
            units.append(["pb", "", page])
    out = []
    for kind, text, pg in units:
        text = MS.sub("", text).replace("%~%", " ").replace("%", " ").replace("صفحة فارغة", " ")
        text = re.sub(r"\s+", " ", text).strip()
        out.append((kind, text, pg))
    return out


def heading_symbol(text: str) -> tuple[str | None, bool]:
    """(symbol, is_intro) for a heading line."""
    if INTRO.search(text[:60]):
        return None, True
    t = re.sub(r"\[[^\]]*\]", " ", text)
    t = re.sub(r"^\s*\d+\s*-\s*", "", t)
    t = re.sub(r"^\s*[\u0600-\u06FF]{1,3}\s*-\s*", "", t)  # abjad numbering: "عط - …"
    t = re.sub(r"\(\s*\d+\s*\)", "", t)
    t = t.replace("(", " ").replace(")", " ").strip(" .:،-")
    t = re.sub(r"\s+", " ", t).strip()
    if not t or re.fullmatch(r"[\d\W]+", t):
        return None, False
    if INTRO.search(t[:40]):
        return None, True
    if ORDINAL_ONLY.match(t) or LETTER_BAB.match(t):
        return None, False
    m = re.search(r"(?:^|\s)(?:في|فى|در)\s+(.+)", t)
    if m:
        t = m.group(1)
    elif STRUCT.match(t):
        return None, False
    t = re.sub(r"^(تأويل|تاويل|تعبير|ذكر|بيان)\s+", "", t)
    t = re.sub(r"^(رؤيا|رؤية|الرؤيا|رؤيه|روية|رويا|رؤيته)\s+", "", t)
    t = re.sub(r"^و(?=ال)", "", t)
    t = t.strip(" .:،-")
    if len(t) < 2:
        return None, False
    return t[:120], False


def headword(par: str, book: Book) -> tuple[str, str] | None:
    if book.paren:
        m = re.match(r"^-?\s*\(([^()]{1,60})\)\s*[:.-]?\s*(.*)$", par)
        if m:
            hw, rest = m.group(1).strip(), m.group(2)
            am = re.match(r"^(?:و|ف)?أما\s+(.{2,40})$", hw)
            if am:  # "(وأما السكر) …" introduces a new symbol
                return am.group(1).strip(), rest
            dash = par.startswith("-")
            words = hw.split()
            if "..." not in hw and not STOP.match(hw) and len(words) <= (8 if dash else 4) and rest:
                return hw, rest
    if book.numbered:
        m = re.match(r"^\[\d+\]\s*فصل\s*:\s*([^:]{2,40}?)\s*:\s*(.+)$", par)
        if m:
            return m.group(1).strip(), m.group(2)
        m = re.match(r"^\[\d+\]\s*([^\s:\-–]+(?: [^\s:\-–]+)?)\s*(?:-|:)\s*(.*)$", par)
        if m and not STOP.match(m.group(1)) and not STRUCT.match(m.group(1)):
            return m.group(1).strip(), m.group(2)
    if book.colon:
        m = re.match(r"^([^\s:()\[\]]{2,25}(?: [^\s:()\[\]]{2,25})?)\s*:\s*(.+)$", par)
        if m:
            hw = m.group(1)
            first = hw.split()[0]
            two_ok = len(hw.split()) == 1 or first.startswith("ال")
            if two_ok and not STOP.match(hw) and not STRUCT.match(hw) and not first.startswith(("و", "ف")):
                return hw, m.group(2)
    return None


@dataclass
class Entry:
    symbol: str
    heading: str
    page: str
    parts: list[str] = field(default_factory=list)


def parse_book(book_uri: str, book: Book, meta: dict) -> list[dict]:
    author = book_uri.split(".")[0]
    path = FILES / author / book_uri / book.version
    units = read_version(path)
    repo = f"{max(25, -(-int(book_uri[:4]) // 25) * 25):04d}AH"
    url = RAW.format(repo=repo, path=f"data/{author}/{book_uri}/{book.version}")
    if author == "0606FakhrDinRazi":
        url = RAW.format(repo="RELEASE", path=f"data/{author}/{book_uri}/{book.version}")
    vid = book.version.rsplit(".", 1)[-1] if "." in book.version else book.version
    rows: list[dict] = []
    heading_sym: str | None = None
    heading_txt = ""
    intro = False
    cur: Entry | None = None
    cur_is_hw = False
    page = ""
    last_was_pb = False

    def chunks(parts: list[str]) -> list[str]:
        """Split an over-long merged heading block back into paragraph-sized pieces."""
        out, acc = [], ""
        for part in parts:
            acc = (acc + " " + part).strip()
            if len(acc) >= 1500 or (len(acc) >= 300 and re.search(r"[.!؟?:)»\]]$", acc)):
                out.append(acc)
                acc = ""
        if acc:
            out.append(acc)
        return out

    def flush() -> None:
        nonlocal cur
        if cur and cur.parts:
            joined = re.sub(r"\s+", " ", " ".join(cur.parts)).strip()
            pieces = [joined]
            if not cur_is_hw and len(joined) > 4000 and len(cur.parts) > 1:
                pieces = chunks(cur.parts)
            for meaning in pieces:
                meaning = re.sub(r"\s+", " ", meaning).strip()
                if len(meaning) < 8:
                    continue
                rows.append(
                    {
                        "source": SOURCE,
                        "tradition": book.tradition,
                        "language": book.language,
                        "symbol_raw": cur.symbol,
                        "condition": "",
                        "meaning": meaning,
                        "polarity": "",
                        "domain": "",
                        "url": url,
                        "locator": f"{book_uri}.{vid} | {cur.heading} | {cur.page}".strip(" |"),
                        "license": LICENSE,
                        "rights_holder": RIGHTS,
                        "attributed_author": meta.get("author", ""),
                        "work": meta.get("title", ""),
                        "version": book.version,
                    }
                )
        cur = None

    for kind, text, pg in units:
        if kind == "pb":
            page = pg
            last_was_pb = True
            continue
        if kind == "h":
            if book.fi_headings and not re.search(r"(^|\s)(في|فى)\s", text):
                continue
            flush()
            sym, is_intro = heading_symbol(text)
            if text.strip():
                intro = is_intro
                heading_sym = sym
                heading_txt = text[:150]
            cur_is_hw = False
            last_was_pb = False
            continue
        if intro:
            continue
        hw = headword(text, book)
        if hw:
            flush()
            cur = Entry(hw[0], heading_txt, page, [hw[1]])
            cur_is_hw = True
        elif cur is not None and (cur_is_hw or book.heading_mode == "merge"):
            cur.parts.append(text)
        elif cur is not None and last_was_pb and not re.search(r"[.!؟?:)»\]]$", cur.parts[-1]):
            cur.parts.append(text)  # paragraph broken by a page marker
        elif heading_sym:
            flush()
            cur = Entry(heading_sym, heading_txt, page, [text])
            cur_is_hw = False
        last_was_pb = False
    flush()
    return rows


def load_meta() -> dict[str, dict]:
    csv.field_size_limit(10**9)
    out: dict[str, dict] = {}
    with (FILES / "metadata" / "OpenITI_metadata_2025-1-9.tsv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["book"] in PARSE and r["book"] not in out:
                author = r["author_ar"].split(" :: ")[0].strip()
                lat = r["author_lat_shuhra"] or r["author_lat"]
                out[r["book"]] = {"author": f"{author} ({lat})".strip(), "title": r["title_ar"].split(" :: ")[0]}
    return out


def parse_all() -> None:
    target = DIR / "entries.jsonl"
    if target.exists():
        target.unlink()  # regenerate from raw files on every run
    meta = load_meta()
    total = 0
    for uri, book in PARSE.items():
        rows = parse_book(uri, book, meta.get(uri, {}))
        if uri.startswith("0110IbnSirin"):
            for r in rows:
                r["attributed_author"] += " [attributed]"
        write_entries(SOURCE, rows)
        total += len(rows)
        print(f"{uri}: {len(rows)} entries")
    print("total", total)


if __name__ == "__main__":
    parse_all()
