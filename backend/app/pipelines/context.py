"""What a pipeline gets from the worker: the job, its state, and a way to save progress."""
import asyncio

from ..store.jobstore import Job


class JobFailed(Exception):
    """A failure the user should read; the job is not tried again."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(detail or message)
        self.message = message


class LostLease(Exception):
    """Another worker took the job over; stop without writing anything more."""


class JobContext:
    def __init__(self, s, job: Job, worker: str, lease: int):
        self.s, self.job, self.worker, self.lease = s, job, worker, lease
        self.state = job.state  # pipelines change this in place and call save()
        self._lock = asyncio.Lock()  # panels finish concurrently; their writes must not overtake each other

    async def save(self, **fields) -> None:
        """Writes the state and progress, renewing the lease. Raises LostLease if the job is no longer ours."""
        async with self._lock:
            body = {"state": self.state, "done": self.job.done, "cost_usd": self.job.cost_usd, **fields}
            if not await self.s.queue.update(self.job.id, body, worker=self.worker, lease=self.lease):
                raise LostLease()
