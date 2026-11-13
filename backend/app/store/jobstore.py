"""The job queue: one row per booklet or picture, in Supabase (or a dict in dev and tests).
A worker claims a job with a lease and keeps renewing it. Writes that name a worker only land
while that worker still holds the job, so a job taken over after a stall never has two writers."""
import copy
import secrets
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from .supabase import UUID, Supabase

ACTIVE = ("queued", "running")


class Busy(Exception):
    """The user already has an exclusive job queued or running."""


class Duplicate(Exception):
    """A job with this dedupe key already exists; job is that one."""

    def __init__(self, job: "Job"):
        super().__init__(job.id)
        self.job = job


class Job(BaseModel):
    id: str
    user_id: str
    kind: str
    status: str = "queued"  # queued | running | done | failed
    input: dict = {}
    state: dict = {}  # what the pipeline has made so far; enough to pick up after a restart
    error: str = ""
    done: int = 0
    total: int = 1
    attempts: int = 0
    worker: str = ""
    cost_usd: float = 0
    dream_id: str | None = None  # the dream the job works for, when there is one
    parent_id: str | None = None  # the job that queued this one, in a chain
    dedupe_key: str = ""  # the same key for the same user and kind never makes a second job
    priority: int = 0
    exclusive: bool = True
    run_after: datetime | None = None  # a queued job waits until then (backoff after a transient error)
    created_at: datetime | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _kind(kind: str):
    from ..pipelines.registry import check  # late: the pipelines import the services, which import this

    return check(kind)


def _row(user_id: str, kind: str, input: dict, total: int, dream_id, parent_id, dedupe_key: str) -> dict:
    k = _kind(kind)
    row = {"user_id": user_id, "kind": kind, "input": input, "total": total, "priority": k.priority, "exclusive": k.exclusive}
    if dream_id:
        row["dream_id"] = dream_id
    if parent_id:
        row["parent_id"] = parent_id
    if dedupe_key:
        row["dedupe_key"] = dedupe_key
    return row


class SupabaseJobs:
    def __init__(self, sb: Supabase):
        self.sb = sb

    async def _call(self, method: str, path: str, params=None, body=None, prefer: str = ""):
        res = await self.sb._do(method, path, self.sb.key, json_body=body, prefer=prefer, params=params)
        return res, (res.json() if res.content.strip() else [])

    async def _rest(self, method: str, params=None, body=None, prefer: str = "") -> list[dict]:
        res, rows = await self._call(method, "/rest/v1/jobs", params, body, prefer)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"jobs: status {res.status_code}: {res.text.strip()[:300]}")
        return rows

    async def create(self, user_id: str, kind: str, input: dict, total: int, request_id: str = "", *,
                     dream_id: str | None = None, parent_id: str | None = None, dedupe_key: str = "") -> Job:
        body = _row(user_id, kind, input, total, dream_id, parent_id, dedupe_key)
        if request_id:
            body["id"] = request_id
        res, rows = await self._call("POST", "/rest/v1/jobs", body=body, prefer="return=representation")
        if res.status_code == 409:  # jobs_dedupe_idx or jobs_one_active_idx
            if dedupe_key:
                params = {"user_id": f"eq.{user_id}", "kind": f"eq.{kind}", "dedupe_key": f"eq.{dedupe_key}", "limit": "1"}
                if found := await self._rest("GET", params):
                    raise Duplicate(Job(**found[0]))
            raise Busy()
        if res.status_code // 100 != 2 or len(rows) != 1:
            raise RuntimeError(f"jobs: create status {res.status_code}: {res.text.strip()[:300]}")
        return Job(**rows[0])

    async def get(self, job_id: str, user_id: str) -> Job | None:
        if not UUID.match(job_id):
            return None
        rows = await self._rest("GET", {"id": f"eq.{job_id}", "user_id": f"eq.{user_id}"})
        return Job(**rows[0]) if rows else None

    async def for_dream(self, user_id: str, dream_id: str) -> list[Job]:
        """The user's jobs for one dream, oldest first."""
        if not UUID.match(dream_id):
            return []
        params = {"user_id": f"eq.{user_id}", "dream_id": f"eq.{dream_id}", "order": "created_at",
                  "select": "id,user_id,kind,status,done,total,error,dream_id,parent_id,created_at", "limit": "100"}
        return [Job(**r) for r in await self._rest("GET", params)]

    async def active(self, user_id: str) -> bool:
        params = {"user_id": f"eq.{user_id}", "status": f"in.({','.join(ACTIVE)})", "select": "id", "limit": "1"}
        return bool(await self._rest("GET", params))

    async def count_since(self, user_id: str, since: datetime) -> int:
        """Jobs the user started since then; failed ones do not count against them."""
        params = {"user_id": f"eq.{user_id}", "status": "neq.failed", "created_at": f"gte.{since.isoformat()}", "select": "id", "limit": "1000"}
        return len(await self._rest("GET", params))

    async def depth(self) -> int:
        return len(await self._rest("GET", {"status": f"in.({','.join(ACTIVE)})", "select": "id", "limit": "1000"}))

    async def finished_before(self, before: datetime, limit: int = 100) -> list[Job]:
        """Done and failed jobs older than before, oldest first."""
        params = {"status": "in.(done,failed)", "created_at": f"lt.{before.isoformat()}", "order": "created_at", "limit": str(limit)}
        return [Job(**r) for r in await self._rest("GET", params)]

    async def delete(self, job_id: str) -> None:
        await self._rest("DELETE", {"id": f"eq.{job_id}"})

    async def claim(self, worker: str, lease: int, max_attempts: int) -> Job | None:
        body = {"p_worker": worker, "p_lease_seconds": lease, "p_max_attempts": max_attempts}
        res, rows = await self._call("POST", "/rest/v1/rpc/claim_job", body=body)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"jobs: claim status {res.status_code}: {res.text.strip()[:300]}")
        return Job(**rows[0]) if rows else None

    async def update(self, job_id: str, fields: dict, worker: str = "", lease: int = 0) -> bool:
        """Writes fields; with a worker, only while it still holds the running job. lease renews it."""
        body = {**fields, "updated_at": _now().isoformat()}
        if lease:
            body["lease_until"] = (_now() + timedelta(seconds=lease)).isoformat()
        params = {"id": f"eq.{job_id}"}
        if worker:
            params |= {"worker": f"eq.{worker}", "status": "eq.running"}
        return len(await self._rest("PATCH", params, body, prefer="return=representation")) == 1


class MemoryJobs:
    """The same queue in a dict, for DREAMLIB_DEV_AUTH=1 and the tests. Lost on restart."""

    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.leases: dict[str, datetime] = {}

    async def create(self, user_id: str, kind: str, input: dict, total: int, request_id: str = "", *,
                     dream_id: str | None = None, parent_id: str | None = None, dedupe_key: str = "") -> Job:
        row = _row(user_id, kind, copy.deepcopy(input), total, dream_id, parent_id, dedupe_key)
        if dedupe_key:
            for j in self.jobs.values():
                if (j.user_id, j.kind, j.dedupe_key) == (user_id, kind, dedupe_key):
                    raise Duplicate(j.model_copy(deep=True))
        if request_id and request_id in self.jobs:
            raise Busy()
        if row["exclusive"] and any(j.user_id == user_id and j.exclusive and j.status in ACTIVE for j in self.jobs.values()):
            raise Busy()
        job = Job(id=request_id or secrets.token_hex(12), created_at=_now(), **row)
        self.jobs[job.id] = job
        return job.model_copy(deep=True)

    async def get(self, job_id: str, user_id: str) -> Job | None:
        j = self.jobs.get(job_id)
        return j.model_copy(deep=True) if j and j.user_id == user_id else None

    async def for_dream(self, user_id: str, dream_id: str) -> list[Job]:
        mine = [j for j in self.jobs.values() if j.user_id == user_id and j.dream_id == dream_id]
        return [j.model_copy(deep=True) for j in sorted(mine, key=lambda j: j.created_at)]

    async def active(self, user_id: str) -> bool:
        return any(j.user_id == user_id and j.status in ACTIVE for j in self.jobs.values())

    async def count_since(self, user_id: str, since: datetime) -> int:
        return sum(1 for j in self.jobs.values() if j.user_id == user_id and j.status != "failed" and j.created_at >= since)

    async def depth(self) -> int:
        return sum(1 for j in self.jobs.values() if j.status in ACTIVE)

    async def finished_before(self, before: datetime, limit: int = 100) -> list[Job]:
        old = sorted((j for j in self.jobs.values() if j.status in ("done", "failed") and j.created_at < before), key=lambda j: j.created_at)
        return [j.model_copy(deep=True) for j in old[:limit]]

    async def delete(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)
        self.leases.pop(job_id, None)

    async def claim(self, worker: str, lease: int, max_attempts: int) -> Job | None:
        now = _now()
        expired = [j for j in self.jobs.values() if j.status == "running" and self.leases.get(j.id, now) < now]
        for j in expired:
            if j.attempts >= max_attempts:
                j.status, j.error = "failed", "iş tamamlanamadı, tekrar dene"
        for j in sorted(self.jobs.values(), key=lambda j: (-j.priority, j.created_at)):
            if (j.status == "queued" and (j.run_after is None or j.run_after <= now)) or (j.status == "running" and self.leases.get(j.id, now) < now):
                j.status, j.attempts, j.worker = "running", j.attempts + 1, worker
                self.leases[j.id] = now + timedelta(seconds=lease)
                return j.model_copy(deep=True)
        return None

    async def update(self, job_id: str, fields: dict, worker: str = "", lease: int = 0) -> bool:
        j = self.jobs.get(job_id)
        if not j or (worker and (j.worker != worker or j.status != "running")):
            return False
        fields = copy.deepcopy(fields)
        if "lease_until" in fields:  # only ever cleared, when a job goes back to the queue
            del fields["lease_until"]
            self.leases.pop(job_id, None)
        if isinstance(fields.get("run_after"), str):
            fields["run_after"] = datetime.fromisoformat(fields["run_after"])
        for k, v in fields.items():
            setattr(j, k, v)
        if lease:
            self.leases[job_id] = _now() + timedelta(seconds=lease)
        return True
