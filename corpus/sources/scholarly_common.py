"""Shared helpers for the open-access scholarly slice (europepmc, openalex,
arxiv, oapen, ijodr, doaj).

All network access still goes through `corpus.fetch.Fetcher`; `Polite` only
adds per-host pacing on top of it (robots.txt Crawl-delay and documented API
limits), plus content validation before a body is recorded in the manifest.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from corpus.fetch import CONTACT, ROBOT_AGENTS, ROOT, Blocked, Fetcher, Meta

MAILTO = CONTACT if "@" in CONTACT else ""  # polite-pool e-mail for OpenAlex and Crossref; empty when unset

# --------------------------------------------------------------------------
# licences


def norm_license(raw: str | None) -> str:
    """Map free-form licence strings/URLs to short codes (cc-by, cc-by-nc-nd, cc0, pd...)."""
    if not raw:
        return "unknown"
    s = raw.strip().lower()
    if "publicdomain/zero" in s or s in ("cc0", "cc 0", "cc-0") or "cc0" in s:
        return "cc0"
    if "publicdomain/mark" in s or s in ("pd", "public-domain", "public domain"):
        return "public-domain"
    m = re.search(r"creativecommons\.org/licenses/([a-z\-]+)", s)
    if m:
        return "cc-" + m.group(1).strip("-")
    s2 = re.sub(r"[\s_]+", "-", s)
    s2 = s2.replace("cc-by-", "cc-by-").replace("ccby", "cc-by")
    m = re.match(r"(cc-by(?:-nc)?(?:-sa|-nd)?)", s2)
    if m:
        return m.group(1)
    if s2.startswith("cc-by"):
        return "cc-by"
    if "arxiv.org/licenses/nonexclusive" in s:
        return "arxiv-nonexclusive-distrib"
    if "arxiv.org/licenses/assumed" in s:
        return "arxiv-assumed-1991-2003"
    return s


def is_open_license(code: str) -> bool:
    return code.startswith("cc-") or code in ("cc0", "public-domain")


# --------------------------------------------------------------------------
# relevance + topic tags

# Lower-case word forms: the acronym DREAM (trials, DREAM complex, challenges)
# is upper case and does not match.
_DREAM_WORD = re.compile(
    r"\b(dreams?|dreaming|dreamt|dreamed|dreamers?|dreamlike|dream-like|daydream\w*|"
    r"nightmares?|lucid|oneiric\w*|oneiro\w*|hypnagogic|sleep paralysis)\b"
)
_TITLE_DREAM = re.compile(r"\b(Dreams?|Dreaming|Dreamt|Nightmares?|Lucid|Oneir\w+)\b")
_NOISE = re.compile(
    r"(DREAM complex|DREAM challenge|Dream Challenge|DREAMM|American Dream|Chinese Dream|"
    r"China Dream|dream team|dream job|DREAM Act|dreamers? \(DACA\))",
)


def relevance(title: str, abstract: str = "", keywords: list[str] | None = None) -> bool:
    """True when the text uses dream vocabulary as words (not only the DREAM acronym)."""
    title = title or ""
    abstract = abstract or ""
    kw = " ".join(keywords or [])
    low_hits = len(_DREAM_WORD.findall(abstract)) + len(_DREAM_WORD.findall(kw.lower()))
    noise = bool(_NOISE.search(title + " " + abstract))
    if noise and low_hits < 2:
        return False
    if _DREAM_WORD.search(title):  # lower-case word in title
        return True
    if _TITLE_DREAM.search(title) and not title.isupper():
        return True
    return low_hits >= 1


_TAGS: list[tuple[str, str]] = [
    ("nightmare", r"nightmare|bad dream|night terror"),
    ("lucid-dreaming", r"lucid"),
    ("dream-content", r"dream content|dream report|hall.{0,5}van de castle|content analysis"),
    ("dream-recall", r"dream recall|recall of dreams|recall frequency"),
    ("rem-sleep", r"\brem\b|rapid eye movement|paradoxical sleep"),
    ("nrem-sleep", r"nrem|non-rem|slow.wave sleep"),
    ("ptsd-trauma", r"ptsd|post-?traumatic|trauma"),
    ("sleep-paralysis", r"sleep paralysis|old hag|incubus|karabasan"),
    ("parasomnia", r"parasomnia|rem sleep behavio|rbd\b|sleepwalk|somnambul"),
    ("dream-interpretation", r"dream interpretation|interpret\w* (of )?dreams|dream work|dreamwork"),
    ("psychoanalysis", r"freud|psychoanaly|jung|archetyp|analytic psycholog"),
    ("culture-anthropology", r"cultur|anthropolog|ethnograph|indigenous|shaman|folk|ritual|cross-cultural"),
    ("religion-spirituality", r"relig|islam|muslim|christian|biblical|bible|buddh|hindu|spiritual|prophe|quran|qur'an|talmud|sufi"),
    ("history-literature", r"histor|medieval|ancient|antiquity|literature|literary|novel|poem|poetry|narrative|oneirocritic|artemidor"),
    ("dream-symbol", r"symbol|imagery|motif|metaphor"),
    ("neuroscience-eeg", r"\beeg\b|fmri|neural|neuroimaging|cortex|brain"),
    ("memory-consolidation", r"memory consolidation|consolidat|memory reactivation|targeted memory"),
    ("emotion-regulation", r"emotion"),
    ("children", r"child|adolescen|infant|pediatric|paediatric"),
    ("covid", r"covid|pandemic|lockdown|sars-cov"),
    ("medication-drugs", r"medication|drug-induced|beta.blocker|prazosin|antidepress|psychedel|cannabis|melatonin"),
    ("ai-nlp", r"machine learning|deep learning|natural language|\bnlp\b|language model|neural network|automatic analysis"),
    ("consciousness", r"conscious"),
    ("creativity", r"creativ|insight|problem.solving"),
    ("precognition-parapsych", r"precogn|telepath|paranormal|parapsych|psi\b"),
]
_TAGS_RE = [(t, re.compile(p, re.I)) for t, p in _TAGS]


def topic_tags(*texts: str) -> list[str]:
    blob = " ".join(t for t in texts if t)
    return [t for t, rx in _TAGS_RE if rx.search(blob)]


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def inverted_to_text(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def safe_name(s: str, limit: int = 120) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    return s[:limit] or "item"


# --------------------------------------------------------------------------
# polite fetching


class Polite:
    """Per-host pacing (robots Crawl-delay, explicit minimums) over a Fetcher."""

    def __init__(self, source: str, license: str = "unknown", rights_holder: str = "unknown",
                 base_delay: float = 1.0, host_min: dict[str, float] | None = None,
                 timeout: float = 120.0) -> None:
        self.meta = Meta(source=source, license=license, rights_holder=rights_holder)
        self.f = Fetcher(self.meta, delay=0.0, timeout=timeout)
        self.base_delay = base_delay
        self.host_min = host_min or {}
        self.last: dict[str, float] = {}
        self.dir = self.f.dir
        self.host_blocks: dict[str, int] = {}

    def crawl_delay(self, url: str) -> float:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        self.f.allowed(url)  # populates robots cache
        rp = self.f._robots.get(base)
        best = 0.0
        if rp is not None:
            for agent in ROBOT_AGENTS + ("*",):
                try:
                    d = rp.crawl_delay(agent)
                except Exception:
                    d = None
                if d:
                    best = max(best, float(d))
        return best

    def _pace(self, url: str) -> None:
        host = urlparse(url).netloc
        need = max(self.base_delay, self.host_min.get(host, 0.0), self.crawl_delay(url))
        gap = time.monotonic() - self.last.get(host, 0.0)
        if gap < need:
            time.sleep(need - gap)
        self.last[host] = time.monotonic()

    def get(self, url: str, name: str | None = None, save: bool = True,
            license: str | None = None, rights_holder: str | None = None,
            expect: tuple[str, ...] | None = None) -> httpx.Response:
        """GET through Fetcher. With `expect` (e.g. ("pdf",)), the body is checked
        before it is recorded; a mismatch raises ValueError and nothing is saved."""
        self._pace(url)
        if license is not None:
            self.meta.license = license
        if rights_holder is not None:
            self.meta.rights_holder = rights_holder
        r = self.f.get(url, name=name, save=save and expect is None)
        self.last[urlparse(url).netloc] = time.monotonic()
        if expect is not None:
            kind = sniff(r)
            if kind not in expect:
                raise ValueError(f"expected {expect}, got {kind} ({r.headers.get('content-type','')}) for {url}")
            if save and not self.f.seen(url):
                self.f._record(url, r, name)
        return r

    def seen(self, url: str) -> bool:
        return self.f.seen(url)

    def block(self, url: str, reason: str) -> None:
        self.f._block(url, reason)


def sniff(r: httpx.Response) -> str:
    body = r.content[:2048]
    ct = r.headers.get("content-type", "").lower()
    if body.startswith(b"%PDF"):
        return "pdf"
    if body.lstrip().startswith(b"<?xml") or "xml" in ct:
        if b"<html" in body.lower():
            return "html"
        return "xml"
    if b"<html" in body.lower() or b"<!doctype html" in body.lower() or "html" in ct:
        return "html"
    if "epub" in ct or body.startswith(b"PK"):
        return "epub"
    if "json" in ct:
        return "json"
    if "text/plain" in ct:
        return "text"
    return "other"


# --------------------------------------------------------------------------
# metadata table


class MetaTable:
    """raw/<source>/metadata.jsonl, keyed by `id`; rewriting keeps the latest row."""

    def __init__(self, source: str) -> None:
        self.path = ROOT / source / "metadata.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows: dict[str, dict] = {}
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        row = json.loads(line)
                        self.rows[row["id"]] = row

    def put(self, row: dict) -> None:
        self.rows[row["id"]] = {**self.rows.get(row["id"], {}), **row}

    def get(self, key: str) -> dict | None:
        return self.rows.get(key)

    def save(self) -> None:
        tmp = self.path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for row in self.rows.values():
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp.replace(self.path)


def folder_bytes(source: str) -> int:
    d = ROOT / source
    return sum(p.stat().st_size for p in d.rglob("*") if p.is_file())


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


__all__ = [
    "Blocked", "MAILTO", "MetaTable", "Polite", "ROOT", "folder_bytes", "inverted_to_text",
    "is_open_license", "load_jsonl", "norm_license", "relevance", "safe_name", "sniff",
    "strip_tags", "topic_tags",
]
