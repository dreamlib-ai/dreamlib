"""Daily allowances and per-user locks in Postgres (supabase/migrations/20261014000006_quota_locks.sql), so every API process
counts the same calls and sees the same lock."""
import secrets
from datetime import datetime, timedelta, timezone

from .supabase import Supabase


class SupabaseQuota:
    def __init__(self, sb: Supabase):
        self.sb = sb

    async def _rpc(self, name: str, body: dict):
        res = await self.sb._do("POST", f"/rest/v1/rpc/{name}", self.sb.key, json_body=body)
        if res.status_code != 200:
            raise RuntimeError(f"quota: {name} status {res.status_code}: {res.text.strip()[:300]}")
        return res.json()

    async def take(self, user_id: str, kind: str, limit: int, window: int) -> bool:
        """Uses one call of the allowance; False when it is used up."""
        return bool(await self._rpc("take_call", {"p_user": user_id, "p_kind": kind, "p_limit": limit, "p_window_seconds": window}))

    async def lock(self, user_id: str, seconds: int, no_jobs: bool) -> str:
        """The lock's token, or '' when the user already holds one (or has a job going, with no_jobs)."""
        token = secrets.token_hex(8)
        ok = await self._rpc("lock_user", {"p_user": user_id, "p_token": token, "p_seconds": seconds, "p_no_jobs": no_jobs})
        return token if ok else ""

    async def unlock(self, user_id: str, token: str) -> None:
        params = {"user_id": f"eq.{user_id}", "token": f"eq.{token}"}
        res = await self.sb._do("DELETE", "/rest/v1/user_locks", self.sb.key, params=params)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"quota: unlock status {res.status_code}")

    async def sweep(self, window: int) -> None:
        """Drops call records older than the window; take_call only cleans up for users who come back."""
        before = (datetime.now(timezone.utc) - timedelta(seconds=window)).isoformat()
        res = await self.sb._do("DELETE", "/rest/v1/call_log", self.sb.key, params={"created_at": f"lt.{before}"})
        if res.status_code // 100 != 2:
            raise RuntimeError(f"quota: sweep status {res.status_code}")
