"""Persian classics: Tiflisi, Kamil al-Ta'bir (archive.org item kamil-al-tabir).

The item is a 2022 rewrite by Dr. Mohammad Reza Ardalan marked Public Domain Mark
1.0 on archive.org (not verified for the rewrite). The book is organised by bab
(chapter), not alphabetically, and the OCR runs entries together, so entries.jsonl
holds chapter-level rows only (symbol_raw = chapter heading line).

Run: backend/.venv/Scripts/python -m corpus.sources.persian_classics
"""

from __future__ import annotations

import re

from corpus.fetch import ROOT, write_entries
from corpus.sources.scholarly_common import Polite

SOURCE = "persian-classics"
LIC = "CC Public Domain Mark 1.0 (as marked on archive.org; modern 2022 rewrite, rights unverified)"
RH = "Uploader-marked PD; Tiflisi (6th c. AH); rewrite/glossary Dr. Mohammad Reza Ardalan (2022)"
ITEM = "https://archive.org/download/kamil-al-tabir/"
URL = "https://archive.org/details/kamil-al-tabir"


def main() -> None:
    p = Polite(SOURCE, license=LIC, rights_holder=RH, base_delay=2)
    p.get("https://archive.org/metadata/kamil-al-tabir", name="metadata.json")
    p.get(ITEM + "kamil%20al%20tabir_djvu.txt", name="kamil_al_tabir_djvu.txt")
    p.get(ITEM + "kamil%20al%20tabir.pdf", name="kamil_al_tabir.pdf", expect=("pdf",))
    txt = (ROOT / SOURCE / "files" / "kamil_al_tabir_djvu.txt").read_text(encoding="utf-8")
    lines = txt.splitlines()
    heads = [i for i, l in enumerate(lines) if re.match(r"^\s*[باپ]ب\s", l) or l.startswith("باب ")]
    rows = []
    for n, i in enumerate(heads):
        j = heads[n + 1] if n + 1 < len(heads) else len(lines)
        body = " ".join(l.strip() for l in lines[i:j] if l.strip())
        if len(body) < 400:  # table-of-contents lines
            continue
        head = lines[i].strip()
        rows.append({
            "source": SOURCE, "tradition": "islamic-persian", "language": "fa",
            "symbol_raw": head[:160], "condition": "", "meaning": body, "polarity": "bilinmiyor",
            "domain": "", "url": URL, "locator": f"chapter-heading line {i + 1} (chapter-level, not symbol-level)",
            "license": LIC, "rights_holder": RH, "attributed_author": "Abu'l-Fazl Hubaysh b. Ibrahim Tiflisi",
        })
    path = ROOT / SOURCE / "entries.jsonl"
    if path.exists():
        path.unlink()
    write_entries(SOURCE, rows)
    print("chapter rows", len(rows))


if __name__ == "__main__":
    main()
