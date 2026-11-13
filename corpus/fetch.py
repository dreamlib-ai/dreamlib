"""Shared polite fetcher for the dream corpus.

Every source script uses `Fetcher`: it checks robots.txt (for our agent and
for ClaudeBot / anthropic-ai), waits between requests per host, never retries
around 401/403 or bot protection, and appends one manifest row per file.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(os.environ.get("CORPUS_ROOT", "corpus-data/raw"))  # raw data stays outside git
CONTACT = os.environ.get("CORPUS_CONTACT", "https://github.com/dreamlib-ai/dreamlib")  # set your own e-mail when you run collectors
USER_AGENT = f"DreamlibCorpusBot/0.1 (+{CONTACT}; research)"
ROBOT_AGENTS = ("DreamlibCorpusBot", "ClaudeBot", "anthropic-ai", "Claude-User")


class Blocked(Exception):
    """robots.txt or the server refused the request; do not work around it."""


@dataclass
class Meta:
    source: str
    license: str = "unknown"
    rights_holder: str = "unknown"
    tradition: str = ""


class Fetcher:
    def __init__(self, meta: Meta, delay: float = 1.5, timeout: float = 60.0) -> None:
        self.meta = meta
        self.delay = delay
        self.dir = ROOT / meta.source
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest = self.dir / "manifest.jsonl"
        self.blocked_log = self.dir / "blocked.jsonl"
        self.client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last: dict[str, float] = {}
        self._seen = self._load_seen()

    def _load_seen(self) -> set[str]:
        if not self.manifest.exists():
            return set()
        with self.manifest.open(encoding="utf-8") as f:
            return {json.loads(line)["url"] for line in f if line.strip()}

    def _wait(self, host: str) -> None:
        gap = time.monotonic() - self._last.get(host, 0.0)
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last[host] = time.monotonic()

    def allowed(self, url: str) -> bool:
        parts = urlparse(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                self._wait(parts.netloc)
                r = self.client.get(base + "/robots.txt")
                if r.status_code in (401, 403):
                    rp = None  # robots itself refused: treat as disallowed
                elif r.status_code >= 400:
                    rp.parse([])  # no robots.txt: everything allowed
                else:
                    rp.parse(r.text.splitlines())
            except httpx.HTTPError:
                rp.parse([])
            self._robots[base] = rp
        rp = self._robots[base]
        return rp is not None and all(rp.can_fetch(agent, url) for agent in ROBOT_AGENTS)

    def _block(self, url: str, reason: str) -> None:
        row = {"url": url, "reason": reason, "at": datetime.now(timezone.utc).isoformat()}
        with self.blocked_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def get(self, url: str, name: str | None = None, save: bool = True) -> httpx.Response:
        """Fetch a URL politely; save body under the source folder and log it."""
        if not self.allowed(url):
            self._block(url, "robots")
            raise Blocked(f"robots.txt disallows {url}")
        host = urlparse(url).netloc
        for attempt in range(3):
            self._wait(host)
            try:
                r = self.client.get(url)
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in (401, 403, 451):
                self._block(url, f"http {r.status_code}")
                raise Blocked(f"{r.status_code} for {url}")
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(30 * (attempt + 1))
                continue
            break
        r.raise_for_status()
        if save and url not in self._seen:
            self._record(url, r, name)
        return r

    def _record(self, url: str, r: httpx.Response, name: str | None) -> None:
        body = r.content
        digest = hashlib.sha256(body).hexdigest()
        rel = Path("files") / (name or digest[:24])
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        row = {
            "url": url,
            "final_url": str(r.url),
            "status": r.status_code,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sha256": digest,
            "bytes": len(body),
            "content_type": r.headers.get("content-type", ""),
            "path": rel.as_posix(),
            "source": self.meta.source,
            "license": self.meta.license,
            "rights_holder": self.meta.rights_holder,
            "tradition": self.meta.tradition,
        }
        with self.manifest.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._seen.add(url)

    def seen(self, url: str) -> bool:
        return url in self._seen


def write_entries(source: str, rows: list[dict]) -> Path:
    """Append extracted symbol rows (see README schema) to entries.jsonl."""
    path = ROOT / source / "entries.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
