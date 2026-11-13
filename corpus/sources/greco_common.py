"""Shared helpers for the Greco-Roman / Byzantine / Jewish / Egyptian / Mesopotamian slice.

Only parsing utilities live here; every HTTP request still goes through
`corpus.fetch.Fetcher` in the individual source scripts.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from corpus.fetch import ROOT, Blocked, Fetcher

FIELDS = (
    "source", "tradition", "language", "symbol_raw", "condition", "meaning", "polarity",
    "domain", "url", "locator", "license", "rights_holder", "attributed_author",
)


def row(**kw) -> dict:
    """Build an entries.jsonl row with every README field present (unknown = empty)."""
    out = {k: kw.pop(k, "") for k in FIELDS}
    if not out["polarity"]:
        out["polarity"] = "bilinmiyor"
    out.update({k: v for k, v in kw.items() if v not in (None, "")})
    return out


def reset_entries(source: str) -> Path:
    path = ROOT / source / "entries.jsonl"
    if path.exists():
        path.unlink()
    return path


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def log_block(fetcher: Fetcher, url: str, reason: str) -> None:
    """Record a refusal that Fetcher itself does not classify (bot challenge, lending-only item...)."""
    fetcher._block(url, reason)  # noqa: SLF001 - same log file Fetcher uses


def try_get(fetcher: Fetcher, url: str, name: str | None = None, save: bool = True):
    """Fetch; return response or None. Blocks/errors are logged, never worked around."""
    try:
        r = fetcher.get(url, name=name, save=save)
    except Blocked as e:
        print("BLOCKED", e)
        return None
    except Exception as e:  # network / 404: note it and continue
        print("ERR", type(e).__name__, str(e)[:160], url)
        with (fetcher.dir / "errors.jsonl").open("a", encoding="utf-8") as fh:  # not a block: 404, timeout...
            fh.write(json.dumps({"url": url, "error": f"{type(e).__name__}: {str(e)[:160]}", "at": now()}) + "\n")
        return None
    if r.status_code == 202 and not r.content:
        log_block(fetcher, url, "http 202 empty body (bot challenge); not bypassed")
        print("CHALLENGE", url)
        return None
    print("OK", r.status_code, len(r.content), url)
    return r


def read_saved(fetcher: Fetcher, url: str) -> bytes | None:
    """Read the stored body of an already fetched URL from the manifest."""
    if not fetcher.manifest.exists():
        return None
    with fetcher.manifest.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            m = json.loads(line)
            if m["url"] == url:
                p = fetcher.dir / m["path"]
                if p.exists():
                    return p.read_bytes()
    return None


def get_or_load(fetcher: Fetcher, url: str, name: str | None = None) -> bytes | None:
    body = read_saved(fetcher, url)
    if body is not None:
        return body
    r = try_get(fetcher, url, name=name)
    return r.content if r is not None else None


# ---------- TEI (EEBO-TCP) ----------

def tei_clean(fragment: str, long_s: bool = True) -> str:
    """Plain text from a TCP TEI fragment: joins EOL hyphens, marks gaps with a bullet."""
    s = re.sub(r'<g ref="char:EOLhyphen"\s*/>\s*', "", fragment)
    s = re.sub(r"<gap[^>]*>.*?</gap>", "•", s, flags=re.S)
    s = re.sub(r"<gap[^>]*/>", "•", s)
    s = re.sub(r"<note[^>]*>.*?</note>", " ", s, flags=re.S)
    s = re.sub(r'<g ref="char:punc">(.*?)</g>', r"\1", s)
    s = re.sub(r"<pb[^>]*/>", " ", s)
    s = re.sub(r"<lb[^>]*/>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    if long_s:
        s = s.replace("ſ", "s")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:?!̀-ͯ])", r"\1", s)
    return s


def tei_sections(xml: str, div_type: str = "section"):
    """Yield dicts (book, idx, head, body, paras) for <div type=section> in TCP texts."""
    book = ""
    pos = 0
    idx = 0
    pat = re.compile(r'<div[^>]*type="(book|%s)"[^>]*>' % re.escape(div_type))
    for m in pat.finditer(xml):
        if m.group(1) == "book":
            bm = re.search(r'n="([^"]+)"', m.group(0))
            book = bm.group(1) if bm else str(int(book or 0) + 1)
            idx = 0
            continue
        start = m.end()
        # section ends at next div open or close of this div (sections are not nested in these texts)
        nxt = re.compile(r"<div[ >]|</div>").search(xml, start)
        end = nxt.start() if nxt else len(xml)
        frag = xml[start:end]
        hm = re.search(r"<head[^>]*>(.*?)</head>", frag, re.S)
        head = tei_clean(hm.group(1)) if hm else ""
        body = tei_clean(frag[hm.end():] if hm else frag)
        idx += 1
        paras = [tei_clean(p) for p in re.findall(r"<p[ >].*?</p>|<p>.*?</p>", frag, re.S)]
        yield {"book": book, "idx": idx, "head": head, "body": body, "paras": [p for p in paras if p]}
        pos = end


SENT_SPLIT = re.compile(r"(?<=[.;:!?])\s+(?=[A-ZÀ-ɏ֐-׿])")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()
