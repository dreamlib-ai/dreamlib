"""Every interpretation and every indexing pass as its own `analyses` row, with versions (M3).

A row is written when the work is done; an interpretation is made before the dream is saved, so its row
starts without a dream and is attached when the dream is saved with its id (analysisId)."""
import hashlib
import uuid
from datetime import datetime, timezone

from .supabase import UUID, Supabase


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SupabaseAnalyses:
    def __init__(self, sb: Supabase):
        self.sb = sb

    async def add(self, user_id: str, pipeline: str, output: dict, *, prompt: str = "", model: str = "",
                  input_text: str = "", dream_id: str = "") -> str:
        row = {"user_id": user_id, "pipeline": pipeline, "prompt": prompt, "model": model,
               "input_sha256": digest(input_text) if input_text else "", "output": output}
        if dream_id and UUID.match(dream_id):
            row["dream_id"] = dream_id
        res = await self.sb._do("POST", "/rest/v1/analyses", self.sb.key, json_body=row, prefer="return=representation")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"analyses: status {res.status_code}: {res.text.strip()[:300]}")
        return res.json()[0]["id"]

    async def attach(self, user_id: str, analysis_id: str, dream_id: str) -> bool:
        """Ties a not yet attached row of this user to the dream; False when there is no such row."""
        if not (UUID.match(analysis_id) and UUID.match(dream_id)):
            return False
        params = {"id": f"eq.{analysis_id}", "user_id": f"eq.{user_id}", "dream_id": "is.null"}
        res = await self.sb._do("PATCH", "/rest/v1/analyses", self.sb.key, json_body={"dream_id": dream_id},
                                params=params, prefer="return=representation")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"analyses: attach status {res.status_code}: {res.text.strip()[:300]}")
        return bool(res.json())

    async def for_dream(self, user_id: str, dream_id: str) -> list[dict]:
        params = {"user_id": f"eq.{user_id}", "dream_id": f"eq.{dream_id}", "order": "created_at.desc", "limit": "50"}
        res = await self.sb._do("GET", "/rest/v1/analyses", self.sb.key, params=params)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"analyses: list status {res.status_code}: {res.text.strip()[:300]}")
        return res.json()


class MemoryAnalyses:
    """The same rows in a list, for DREAMLIB_DEV_AUTH=1 and the tests."""

    def __init__(self):
        self.rows: list[dict] = []

    async def add(self, user_id: str, pipeline: str, output: dict, *, prompt: str = "", model: str = "",
                  input_text: str = "", dream_id: str = "") -> str:
        row = {"id": str(uuid.uuid4()), "user_id": user_id, "dream_id": dream_id or None, "pipeline": pipeline,
               "prompt": prompt, "model": model, "input_sha256": digest(input_text) if input_text else "",
               "output": output, "created_at": datetime.now(timezone.utc).isoformat()}
        self.rows.append(row)
        return row["id"]

    async def attach(self, user_id: str, analysis_id: str, dream_id: str) -> bool:
        for row in self.rows:
            if row["id"] == analysis_id and row["user_id"] == user_id and row["dream_id"] is None:
                row["dream_id"] = dream_id
                return True
        return False

    async def for_dream(self, user_id: str, dream_id: str) -> list[dict]:
        rows = [r for r in self.rows if r["user_id"] == user_id and r["dream_id"] == dream_id]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)
