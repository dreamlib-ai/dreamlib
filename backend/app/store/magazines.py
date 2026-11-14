"""One magazine per dream (G4): the `spec` the reader draws, kept until the dream goes. G6: shared by an
unguessable slug once its owner opens it to anyone with the link."""
import re
import secrets
from datetime import datetime, timezone

from .supabase import UUID, Supabase


SLUG = re.compile(r"^[A-Za-z0-9_-]{8,32}$")
SHARED = ("link", "public")


def new_slug() -> str:
    return secrets.token_urlsafe(9)  # 12 characters, 72 bits: not guessable, short enough to paste


class SupabaseMagazines:
    def __init__(self, sb: Supabase):
        self.sb = sb

    async def put(self, user_id: str, dream_id: str, spec: dict, cover_path: str, revision: int) -> str:
        """Writes the dream's magazine, replacing the one before; visibility and share link stay as they were."""
        row = {"user_id": user_id, "dream_id": dream_id, "spec": spec, "cover_path": cover_path,
               "dream_revision": revision, "updated_at": datetime.now(timezone.utc).isoformat()}
        res = await self.sb._do("POST", "/rest/v1/magazines", self.sb.key, json_body=row, params={"on_conflict": "dream_id"},
                                prefer="resolution=merge-duplicates,return=representation")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"magazines: put status {res.status_code}: {res.text.strip()[:300]}")
        return res.json()[0]["id"]

    async def for_dream(self, user_id: str, dream_id: str) -> dict | None:
        if not UUID.match(dream_id):
            return None
        res = await self.sb._do("GET", "/rest/v1/magazines", self.sb.key,
                                params={"user_id": f"eq.{user_id}", "dream_id": f"eq.{dream_id}"})
        if res.status_code != 200:
            raise RuntimeError(f"magazines: read status {res.status_code}: {res.text.strip()[:300]}")
        rows = res.json()
        return rows[0] if rows else None

    async def share(self, user_id: str, dream_id: str, visibility: str) -> dict | None:
        """Sets who may read it; the first time it is shared it gets a slug that then stays (re-sharing gives the
        same link back). None when the dream has no magazine."""
        row = await self.for_dream(user_id, dream_id)
        if not row:
            return None
        body = {"visibility": visibility}
        if visibility in SHARED and not row.get("share_slug"):
            body["share_slug"] = new_slug()
        res = await self.sb._do("PATCH", "/rest/v1/magazines", self.sb.key, json_body=body,
                                params={"id": f"eq.{row['id']}", "user_id": f"eq.{user_id}"}, prefer="return=representation")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"magazines: share status {res.status_code}: {res.text.strip()[:300]}")
        rows = res.json()
        return rows[0] if rows else None

    async def by_slug(self, slug: str) -> dict | None:
        """A magazine its owner shares, for anyone who has the link; never a private or withdrawn one."""
        if not SLUG.match(slug):
            return None
        res = await self.sb._do("GET", "/rest/v1/magazines", self.sb.key, params={
            "share_slug": f"eq.{slug}", "visibility": "in.(link,public)", "status": "eq.ready"})
        if res.status_code != 200:
            raise RuntimeError(f"magazines: slug read status {res.status_code}")
        rows = res.json()
        return rows[0] if rows else None

    async def remove(self, user_id: str, dream_id: str) -> None:
        if not UUID.match(dream_id):
            return
        res = await self.sb._do("DELETE", "/rest/v1/magazines", self.sb.key,
                                params={"user_id": f"eq.{user_id}", "dream_id": f"eq.{dream_id}"})
        if res.status_code // 100 != 2:
            raise RuntimeError(f"magazines: remove status {res.status_code}")


class MemoryMagazines:
    """The same rows in a dict, for DREAMLIB_DEV_AUTH=1 and the tests."""

    def __init__(self):
        self.rows: dict[str, dict] = {}  # dream_id -> row

    async def put(self, user_id: str, dream_id: str, spec: dict, cover_path: str, revision: int) -> str:
        now = datetime.now(timezone.utc).isoformat()
        prior = self.rows.get(dream_id)
        if prior and prior["user_id"] != user_id:
            raise RuntimeError("magazines: dream belongs to someone else")
        row = prior or {"id": f"mag-{len(self.rows) + 1}", "user_id": user_id, "dream_id": dream_id, "status": "ready",
                        "visibility": "private", "share_slug": None, "created_at": now}
        row.update(spec=spec, cover_path=cover_path, dream_revision=revision, updated_at=now)
        self.rows[dream_id] = row
        return row["id"]

    async def for_dream(self, user_id: str, dream_id: str) -> dict | None:
        row = self.rows.get(dream_id)
        return dict(row) if row and row["user_id"] == user_id else None

    async def share(self, user_id: str, dream_id: str, visibility: str) -> dict | None:
        row = self.rows.get(dream_id)
        if not row or row["user_id"] != user_id:
            return None
        row["visibility"] = visibility
        if visibility in SHARED and not row.get("share_slug"):
            row["share_slug"] = new_slug()
        return dict(row)

    async def by_slug(self, slug: str) -> dict | None:
        for row in self.rows.values():
            if SLUG.match(slug) and row.get("share_slug") == slug and row["visibility"] in SHARED and row["status"] == "ready":
                return dict(row)
        return None

    async def remove(self, user_id: str, dream_id: str) -> None:
        if (row := self.rows.get(dream_id)) and row["user_id"] == user_id:
            del self.rows[dream_id]
