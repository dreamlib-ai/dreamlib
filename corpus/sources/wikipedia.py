"""Wikipedia dream/oneiromancy categories in 25 languages via the MediaWiki API.

Plan: Action API (/w/api.php) category members (2 levels) + wikitext + plain
extracts; fallback REST API (/api/rest_v1/). Both go through Fetcher, which
checks robots.txt. Wikipedia's robots.txt disallows /w/ and /api/ for every
user agent, so the script records the refusal per language and stops: no HTML
scraping of /wiki/ pages, no other workaround.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote

from corpus.fetch import ROOT, Blocked, Fetcher, Meta

SOURCE = "wikipedia"
LANGS = ["en", "tr", "ar", "fa", "ur", "he", "zh", "ja", "ko", "hi", "id", "vi", "th",
         "ru", "de", "fr", "es", "it", "pt", "pl", "el", "la", "sa", "bn", "sw"]
# Seed categories (English names; the API would resolve langlinks per language).
SEED = ["Category:Dreams", "Category:Oneiromancy", "Category:Dream interpretation"]


def api_probe(lang: str) -> str:
    return (f"https://{lang}.wikipedia.org/w/api.php?action=query&list=categorymembers"
            f"&cmtitle={quote(SEED[0])}&cmlimit=500&format=json")


def rest_probe(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote('Dream')}"


def main() -> None:
    f = Fetcher(Meta(SOURCE, license="CC BY-SA 4.0", rights_holder="Wikipedia contributors",
                     tradition="encyclopedic"), delay=1.0)
    status = {}
    for lang in LANGS:
        row = {"api": None, "rest": None}
        for kind, url in (("api", api_probe(lang)), ("rest", rest_probe(lang))):
            try:
                f.get(url, save=False)
                row[kind] = "ok"
            except Blocked as e:
                row[kind] = f"blocked: {e}"
        status[lang] = row
        print(lang, row)
        if row["api"] == "ok" or row["rest"] == "ok":
            # Never reached as of 2026-10: robots.txt disallows both paths.
            raise SystemExit("API reachable: implement collection before rerunning.")
    out = ROOT / SOURCE / "probe_status.json"
    out.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(),
                               "status": status}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
