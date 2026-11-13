"""Probe Korean/Japanese candidate sites that refuse us; Fetcher logs each refusal to blocked.jsonl.

Run: backend/.venv/Scripts/python -m corpus.sources.krjp_blocked
"""
from corpus.fetch import Blocked, Fetcher, Meta

URLS = ["https://www.unseebom.com/dream", "https://www.byeoldam.com/dream", "http://www.unzzang.com/service/dream/free_dream/dream_list.asp",
        "https://namu.wiki/w/%ED%83%9C%EB%AA%BD"]

if __name__ == "__main__":
    f = Fetcher(Meta("krjp-blocked", "n/a", "n/a", "Kore/Japonya"), delay=2.0)
    for u in URLS:
        try:
            f.get(u, save=False)
            print("OK (unexpected)", u)
        except Blocked as e:
            print("blocked", u, e)
        except Exception as e:  # noqa: BLE001
            print("error", u, repr(e)[:100])
