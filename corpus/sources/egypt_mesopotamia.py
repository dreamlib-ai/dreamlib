"""Egypt / Mesopotamia: only metadata of CDLI dream tablets (Oppenheim "Dreams" numbers).

Oppenheim 1956 / Gardiner 1935 are still in copyright or lending-only: not fetched (see notes.md).
CDLI robots.txt asks Crawl-delay 60, so this uses delay=60.

Run: backend/.venv/Scripts/python -m corpus.sources.egypt_mesopotamia
"""
from corpus.fetch import Fetcher, Meta
from corpus.sources.greco_common import log_block, try_get

SOURCE = "egypt-mesopotamia"
IDS = [398330, 396742, 425925, 425465, 236997]


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, license="CDLI metadata (licence not verified on site; treat as unknown)",
                     rights_holder="CDLI (UCLA/Oxford/MPIWG); tablets: British Museum", tradition="mezopotamya"), delay=60)
    for i in IDS:
        try_get(f, f"https://cdli.earth/artifacts/{i}/json", name=f"cdli_P{i:06d}.json")
    log_block(f, "https://archive.org/details/hieraticpapyriin0001alan", "not fetched: Gardiner 1935 lending-only (access-restricted), in copyright")
    log_block(f, "https://archive.org/details/Oppenheim1956AssyrianDreamBook", "not fetched: Oppenheim 1956 likely infringing user upload; rights holder APS/Penn Press")


if __name__ == "__main__":
    main()
