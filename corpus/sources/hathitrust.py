"""HathiTrust: full-view public-domain dream books, allowed endpoints only.

Uses the Bibliographic API (catalog.hathitrust.org/api/volumes) for known
records and keeps only items whose rights code is pd (public domain
worldwide). Full text would come from the plain-text page view
(babel.hathitrust.org/cgi/pt?...;seq=N) only where robots.txt allows. Every
request goes through Fetcher; HathiTrust currently answers non-browser
clients with a Cloudflare challenge (403), which is logged and respected.

Run from repo root:  backend/.venv/Scripts/python -m corpus.sources.hathitrust
"""

from __future__ import annotations

import json
import sys

from corpus.fetch import ROOT, Blocked, Fetcher, Meta

SOURCE = "hathitrust"
# Records named in the research atlas (hint-folk-bati.md) plus catalog searches.
RECORDS = {
    "100832198": "Negelein 1912, Der Traumschlüssel des Jagaddeva (atlas: 'US access only')",
}
CATALOG_SEARCH = [
    "https://catalog.hathitrust.org/Search/Home?lookfor=%22dream+book%22&type=title&ft=ft&setft=true",
    "https://catalog.hathitrust.org/Search/Home?lookfor=dreams&type=subject&ft=ft&setft=true",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    base = ROOT / SOURCE
    f = Fetcher(Meta(source=SOURCE, license="HathiTrust pd (public domain) only", rights_holder="public domain"), delay=3.0)
    status = {"blocked": [], "records": {}}
    for rec, note in RECORDS.items():
        url = f"https://catalog.hathitrust.org/api/volumes/full/recordnumber/{rec}.json"
        try:
            r = f.get(url, name=f"record_{rec}.json")
            items = r.json().get("items", [])
            status["records"][rec] = [{"htid": i.get("htid"), "rights": i.get("rightsCode"), "usRights": i.get("usRightsString")} for i in items]
        except Blocked as e:
            status["blocked"].append({"url": url, "reason": str(e), "note": note})
            print("blocked:", e)
        except Exception as e:
            status["blocked"].append({"url": url, "reason": repr(e), "note": note})
    for url in CATALOG_SEARCH:
        try:
            f.get(url, save=False)
        except Blocked as e:
            status["blocked"].append({"url": url, "reason": str(e)})
            print("blocked:", e)
        except Exception as e:
            status["blocked"].append({"url": url, "reason": repr(e)})
    (base / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
