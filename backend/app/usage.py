"""One `usage` row per paid provider call: who, for which job, which model, how much.

Providers call meter.record() after a call that cost something; who and which job come from the
scope set by the request (current_user) or the worker (run_one), so call sites need not pass them.
Writing a row never breaks the call it describes."""
import logging
from contextvars import ContextVar

from .store.supabase import UUID, Supabase

log = logging.getLogger("dreamlib")

_scope: ContextVar[dict] = ContextVar("usage_scope", default={})


def set_scope(user_id: str = "", job_id: str = "") -> None:
    """Names who the calls in this request or job are for. Each request and job has its own context."""
    _scope.set({"user_id": user_id, "job_id": job_id})


class Meter:
    def __init__(self, sink):
        self.sink = sink  # SupabaseUsage or MemoryUsage

    async def record(self, provider: str, model: str, task: str, units: float, unit: str, cost_usd: float) -> None:
        scope = _scope.get()
        row = {"provider": provider, "model": model, "task": task, "units": units, "unit": unit, "cost_usd": cost_usd,
               "user_id": scope.get("user_id") or None, "job_id": scope.get("job_id") or None}
        try:
            await self.sink.insert(row)
        except Exception:
            log.warning("usage: could not record %s %s", provider, model, exc_info=True)


class SupabaseUsage:
    def __init__(self, sb: Supabase):
        self.sb = sb

    async def insert(self, row: dict) -> None:
        row = {**row, "user_id": _uuid(row["user_id"]), "job_id": _uuid(row["job_id"])}
        res = await self.sb._do("POST", "/rest/v1/usage", self.sb.key, json_body=row, prefer="return=minimal")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"usage: status {res.status_code}: {res.text.strip()[:300]}")


class MemoryUsage:
    """The same rows in a list, for DREAMLIB_DEV_AUTH=1 and the tests."""

    def __init__(self):
        self.rows: list[dict] = []

    async def insert(self, row: dict) -> None:
        self.rows.append(row)


def _uuid(value):
    return value if value and UUID.match(value) else None
