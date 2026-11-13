"""OpenITI: classical Arabic/Persian dream books (ta'bir, ru'ya, ahlam, manam).

Steps
  download  metadata TSV from OpenITI/RELEASE, select dream works, then every
            version (+ yml sidecars) from the per-period repos (OpenITI/0125AH…)
            via raw.githubusercontent.com. The GitHub API (60/h unauthenticated)
            is used only to list each book folder, so versions newer than the
            release are also caught; when the quota is low we fall back to the
            paths in the release metadata.
  parse     split the texts into symbol -> meaning rows (see corpus/README.md).

Run: backend/.venv/Scripts/python -m corpus.sources.openiti [download|parse]
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from pathlib import Path

import httpx

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "openiti"
LICENSE = "CC BY-NC-SA 4.0 (OpenITI Zenodo release); underlying classical works public domain"
RIGHTS = "OpenITI (AKU-ISMC / Univ. Vienna / Univ. Maryland / KITAB); text editions per version yml"
META_URL = "https://raw.githubusercontent.com/OpenITI/RELEASE/master/metadata/OpenITI_metadata_2025-1-9.tsv"
RAW = "https://raw.githubusercontent.com/OpenITI/{repo}/master/{path}"
API = "https://api.github.com/repos/OpenITI/{repo}/contents/{path}"
DIR = ROOT / SOURCE
FILES = DIR / "files"

# Book URIs chosen from a metadata search (title/tags: tacbir, ru'ya, ahlam,
# manam, _AHLAM, "كتب تفسير الأحلام"). Theology "ru'yat Allah", logic
# "kitab al-cibara" and modern fiction titled "ahlam" are left out on purpose.
BOOKS = {
    "0110IbnSirin.MuntakhabKalamFiTafsirAhlam": "dictionary",
    "0256IbnIshaqKindi.NawmWaRuya": "treatise",
    "0259HunaynIbnIshaq.TacbirRuya": "artemidorus",
    "0281IbnAbiDunya.Manamat": "narratives",
    "0350Anonymous.AristutalisFiRuya": "treatise",
    "0410NasrIbnYacqub.QadiriFiTacbir": "dictionary",
    "0413ShaykhMufid.SharhManam": "treatise",
    "0606FakhrDinRazi.TahbirCilmTacbir": "dictionary",
    "0693IbnGhannam.TacbirRuya": "dictionary",
    "0697AbuCabbasShihabDinNabulusi.QawacidTafsirAhlam": "dictionary",
    "0800IbnAhmadAbuCabdAllahSalimi.IsharaIlaCilmCibara": "dictionary",
    "0873IbnShahinZahiri.Isharat": "dictionary",
    "1143CabdGhaniNabulusi.TactirAnam": "dictionary",
    "1270IbnMuhammadIhsaiHanafi.TanbihAfham": "dictionary",
}
SEARCH_LAT = re.compile(r"(Tacbir|Ruya|Ahlam|Manam|Tactir)", re.I)
SEARCH_AR = re.compile(r"(تعبير|الرؤيا|رؤيا|أحلام|الأحلام|منام|المنام|_AHLAM|تفسير الأحلام)")


def period_repo(uri: str) -> str:
    year = int(uri[:4])
    return f"{max(25, math.ceil(year / 25) * 25):04d}AH"


def load_metadata() -> list[dict]:
    csv.field_size_limit(10**9)
    path = FILES / "metadata" / "OpenITI_metadata_2025-1-9.tsv"
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def candidates(rows: list[dict]) -> list[str]:
    """Book URIs whose title/tags look dream-related (for the log / notes)."""
    out = []
    for r in rows:
        if SEARCH_LAT.search(r["book"]) or SEARCH_AR.search(r["title_ar"] + " " + r["tags"]):
            out.append(r["book"])
    return sorted(set(out))


_api_left: int | None = None


def api_list(f: Fetcher, repo: str, path: str) -> list[dict] | None:
    """List a folder through Fetcher (save=False); skip when the hourly quota is nearly gone."""
    global _api_left
    if _api_left is not None and _api_left < 3:
        return None
    try:
        r = f.get(API.format(repo=repo, path=path), save=False)
    except Blocked as e:
        print(f"  api refused for {repo}/{path}: {e}")
        _api_left = 0
        return None
    except httpx.HTTPError as e:
        print(f"  api failed for {repo}/{path}: {str(e).splitlines()[0]}")
        return None
    _api_left = int(r.headers.get("x-ratelimit-remaining", "0"))
    print(f"  api ok {repo}/{path} (remaining {_api_left})")
    return r.json()


def fetch_file(f: Fetcher, repo: str, path: str, local: str) -> bool:
    url = RAW.format(repo=repo, path=path)
    if f.seen(url):
        return True
    try:
        f.get(url, name=local)
        return True
    except Blocked as e:
        print("  blocked", e)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            print("  http", e.response.status_code, url)
    return False


def download() -> None:
    meta = Meta(SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition="islamic-classical")
    f = Fetcher(meta, delay=1.0)
    f.get(META_URL, name="metadata/OpenITI_metadata_2025-1-9.tsv")
    f.get("https://raw.githubusercontent.com/OpenITI/RELEASE/master/README.md", name="metadata/RELEASE_README.md")
    rows = load_metadata()
    by_book: dict[str, list[dict]] = {}
    for r in rows:
        by_book.setdefault(r["book"], []).append(r)
    (DIR / "candidates.txt").write_text("\n".join(candidates(rows)) + "\n", encoding="utf-8")

    for book in BOOKS:
        author = book.split(".")[0]
        repo = period_repo(book)
        folder = f"data/{author}/{book}"
        print(book, "->", repo)
        fetch_file(f, repo, f"data/{author}/{author}.yml", f"{author}/{author}.yml")
        listing = api_list(f, repo, folder)
        if listing:
            for item in listing:
                if item["type"] == "file":
                    fetch_file(f, repo, f"{folder}/{item['name']}", f"{author}/{book}/{item['name']}")
            continue
        # fallback: release metadata paths (extension may differ in the period repo)
        fetch_file(f, repo, f"{folder}/{book}.yml", f"{author}/{book}/{book}.yml")
        for v in by_book.get(book, []):
            name = v["version_uri"]
            fetch_file(f, repo, f"{folder}/{name}.yml", f"{author}/{book}/{name}.yml")
            for ext in ("", ".mARkdown", ".completed", ".inProgress"):
                if fetch_file(f, repo, f"{folder}/{name}{ext}", f"{author}/{book}/{name}{ext}"):
                    break
            else:
                # last resort: the release snapshot
                rel = v["local_path"]
                fetch_file(f, "RELEASE", rel, f"{author}/{book}/{Path(rel).name}")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("download", "all"):
        download()
    if step in ("parse", "all"):
        from corpus.sources.openiti_parse import parse_all

        parse_all()
