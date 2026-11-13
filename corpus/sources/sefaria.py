"""Jewish dream texts via the Sefaria v3 API (no key needed).

Only versions whose Sefaria license is Public Domain / CC0 / CC-BY / CC-BY-SA are downloaded; the license
string is taken from the API response of each version. CC-BY-NC (William Davidson / Koren, JPS 2006...),
"unknown" and "Copyright" versions are skipped and listed in notes.md.

Entries: Berakhot 55a-57b dream-symbol passages ("who sees X in a dream ...") from
A. Cohen 1921 (PD), Sefaria Community Translation (CC0), Wikisource Aramaic (CC-BY-SA) and
Goldschmidt 1929 German (PD). Everything else (Tanakh dream narratives, Zohar, Midrash, Yerushalmi,
Divrei Chalomot, other Bavli passages) is stored raw plus in passages.jsonl.

Run: backend/.venv/Scripts/python -m corpus.sources.sefaria
"""

from __future__ import annotations

import json
import re
import urllib.parse

from corpus.fetch import ROOT, Fetcher, Meta, write_entries
from corpus.sources.greco_common import get_or_load, reset_entries, row, sentences, write_jsonl

SOURCE = "sefaria"
TRADITION = "yahudi"
API = "https://www.sefaria.org/api/v3/texts/"
FREE = {"Public Domain", "PD", "CC0", "CC-BY", "CC-BY-SA"}

BERAKHOT = ["Berakhot.55a", "Berakhot.55b", "Berakhot.56a", "Berakhot.56b", "Berakhot.57a", "Berakhot.57b"]
OTHER_BAVLI = ["Berakhot.10b", "Berakhot.14a", "Shabbat.11a", "Taanit.12b", "Chagigah.5b", "Nedarim.8a",
               "Nedarim.8b", "Sanhedrin.30a", "Horayot.12a", "Gittin.52a", "Yoma.87b"]
OTHER = ["Jerusalem_Talmud_Maaser_Sheni.4.6", "Eikhah_Rabbah.1.1", "Bereshit_Rabbah.68", "Bereshit_Rabbah.89",
         "Zohar,_Vayeshev", "Zohar,_Miketz", "Divrei_Chalomot"]
TANAKH = ["Genesis.20.1-7", "Genesis.28.10-22", "Genesis.31.10-13", "Genesis.31.24", "Genesis.37.5-11",
          "Genesis.40", "Genesis.41", "Numbers.12.6-8", "Deuteronomy.13.2-6", "Judges.7.13-15",
          "I_Samuel.28.6", "I_Samuel.28.15", "I_Kings.3.5-15", "Job.4.12-17", "Job.7.13-14", "Job.33.14-18",
          "Psalms.126.1", "Ecclesiastes.5.2", "Ecclesiastes.5.6", "Isaiah.29.7-8", "Jeremiah.23.25-32",
          "Jeremiah.29.8", "Joel.3.1", "Zechariah.10.2", "Daniel.1.17", "Daniel.2", "Daniel.4", "Daniel.7", "Daniel.8"]

RIGHTS = {
    "Tractate Berakot by A. Cohen, Cambridge University Press, 1921": "public domain (A. Cohen, CUP 1921); hosted by Sefaria (hello@sefaria.org)",
    "Sefaria Community Translation": "Sefaria.org community (CC0); hello@sefaria.org",
    "Wikisource Talmud Bavli": "Hebrew Wikisource contributors (CC-BY-SA); via Sefaria",
}


def lang_param(v: dict) -> str:
    return "hebrew" if v.get("language") == "he" else "english"


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:90]


def flatten(t, path=()):
    if isinstance(t, str):
        yield path, t
    elif isinstance(t, list):
        for i, x in enumerate(t, 1):
            yield from flatten(x, path + (i,))


class Sef:
    def __init__(self) -> None:
        self.f = Fetcher(Meta(source=SOURCE, tradition=TRADITION), delay=1.5)
        self.skipped: list[dict] = []
        self.passages: list[dict] = []
        self.texts: dict[tuple[str, str], tuple[dict, str]] = {}

    def index(self, ref: str) -> list[dict]:
        u = API + urllib.parse.quote(ref) + "?version=all&return_format=text_only"
        self.f.meta.license, self.f.meta.rights_holder = "API listing (no text)", "Sefaria.org"
        body = get_or_load(self.f, u, name=f"{safe(ref)}__versions.json")
        if not body:
            return []
        return json.loads(body).get("available_versions", [])

    def version(self, ref: str, v: dict) -> None:
        title, lic = v["versionTitle"], v.get("license") or "unknown"
        if lic not in FREE:
            self.skipped.append({"ref": ref, "version": title, "license": lic})
            return
        q = urllib.parse.urlencode({"version": f"{lang_param(v)}|{title}", "return_format": "text_only"})
        u = API + urllib.parse.quote(ref) + "?" + q
        self.f.meta.license = lic
        self.f.meta.rights_holder = RIGHTS.get(title, f"{v.get('versionSource') or 'unknown source'}; hosted by Sefaria (hello@sefaria.org)")
        body = get_or_load(self.f, u, name=f"{safe(ref)}__{safe(title)}.json")
        if not body:
            return
        d = json.loads(body)
        vs = [x for x in d.get("versions", []) if x.get("versionTitle") == title] or d.get("versions", [])
        if not vs:
            return
        text = vs[0].get("text")
        page = "https://www.sefaria.org/" + urllib.parse.quote(d.get("ref", ref).replace(" ", "_")) + "?" + urllib.parse.urlencode({"ven" if lang_param(v) == "english" else "vhe": title})
        self.texts[(ref, title)] = (v, page)
        for path, seg in flatten(text):
            if seg.strip():
                self.passages.append({"query_ref": ref, "ref": d.get("ref", ref), "segment": ".".join(map(str, path)),
                                      "version": title, "language": v.get("actualLanguage") or v.get("language"),
                                      "license": lic, "url": page, "text": seg.strip()})

    def run_ref(self, ref: str, only_titles: set[str] | None = None) -> None:
        for v in self.index(ref):
            if only_titles and v["versionTitle"] not in only_titles:
                continue
            self.version(ref, v)


EN_PAT = re.compile(
    r"^(?:\[?(?:One|He|Whoever|Who|If one|If a man|A man|Whosoever)\b[^.;:]{0,25}?)?"
    r"(?:\[?dreams?\]?\s+(?:that\s+)?(?:of\s+)?|sees?\s+|saw\s+)(.{2,120}?)"
    r"(?:\s+in\s+(?:a|his)\s+dream)?\s*[,;:](.*)$", re.I)


def en_entries(seg: str) -> list[tuple[str, str]]:
    out = []
    for s in sentences(seg):
        if not re.search(r"dream", s, re.I):
            continue
        m = EN_PAT.search(s)
        if m and re.search(r"\b(dreams?|sees?|saw)\b", s[:80], re.I):
            out.append((m.group(1).strip(" [],"), s))
    return out


def he_entries(seg: str) -> list[tuple[str, str]]:
    out = []
    parts = re.split(r"(?=\bהרואה\b)", seg)
    for p in parts:
        m = re.match(r"הרואה\s+(.{1,80}?)\s+בחלום", p)
        if m:
            out.append((m.group(1), p.strip()))
    return out


def de_entries(seg: str) -> list[tuple[str, str]]:
    out = []
    for s in sentences(seg):
        m = re.search(r"\bWer\s+(?:im\s+Traume?\s+)?(.{2,100}?)\s+(?:im\s+Traume?\s+)?(?:sieht|träumt)\b", s)
        if m and "Traum" in s:
            out.append((m.group(1).strip(), s))
    return out


def main() -> None:
    s = Sef()
    reset_entries(SOURCE)
    for ref in BERAKHOT + OTHER_BAVLI + OTHER:
        s.run_ref(ref)
    for ref in TANAKH:
        s.run_ref(ref, {"The Holy Scriptures: A New Translation (JPS 1917)", "Tanach with Ta'amei Hamikra"})

    rows = []
    for (ref, title), (v, page) in s.texts.items():
        if ref not in BERAKHOT:
            continue
        lang = v.get("actualLanguage") or v.get("language")
        extractor = {"en": en_entries, "he": he_entries, "de": de_entries}.get(lang)
        if not extractor:
            continue
        for p in (x for x in s.passages if x["version"] == title and x["query_ref"] == ref):
            for sym, meaning in extractor(p["text"]):
                rows.append(row(source=SOURCE, tradition=TRADITION, language="arc" if lang == "he" else lang,
                                symbol_raw=sym, meaning=meaning, url=page,
                                locator=f"{p['ref']}:{p['segment']} ({title})",
                                license=p["license"], rights_holder=RIGHTS.get(title, f"{v.get('versionSource')}; via Sefaria"),
                                attributed_author="Babylonian Talmud, Berakhot 55a-57b (dream chapter)",
                                edition=title))
    write_jsonl(ROOT / SOURCE / "passages.jsonl", s.passages)
    write_jsonl(ROOT / SOURCE / "skipped_versions.jsonl", s.skipped)
    path = write_entries(SOURCE, rows)
    print("passages", len(s.passages), "skipped versions", len(s.skipped), "entries", len(rows), "->", path)


if __name__ == "__main__":
    main()
