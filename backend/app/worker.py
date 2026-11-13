"""Takes jobs off the queue and runs them. Starts inside the API process (DREAMLIB_WORKERS jobs at a
time); `python -m app.worker` runs the same loop on its own, for when the API should not draw.

A job is held with a lease that a heartbeat keeps renewing. If the process dies the lease runs
out and the next worker picks the job up again from its saved state, up to MAX_ATTEMPTS times."""
import asyncio
import logging
import os
import secrets
import socket
from datetime import datetime, timedelta, timezone

from .pipelines import image, manga
from .pipelines.context import JobContext, JobFailed, LostLease
from .services import remove_files
from .store.jobstore import Job

log = logging.getLogger("dreamlib")

LEASE = 60
HEARTBEAT = 15
MAX_ATTEMPTS = 3
IDLE = 5  # seconds between looks at an empty queue; a job made here wakes the worker at once
KEEP_JOBS = timedelta(days=7)  # finished jobs are swept after this; pictures never saved to a dream go with them
SWEEP_EVERY = 6 * 3600

PIPELINES = {
    "manga": (manga.run, manga.MANGA_TIMEOUT, manga.FAILED),
    "image": (image.run, 3 * 60, image.FAILED),
}


class Worker:
    def __init__(self, s, concurrency: int = 2, idle: float = IDLE):
        self.s, self.idle = s, idle
        self.name = f"{socket.gethostname()}-{os.getpid()}-{secrets.token_hex(3)}"
        self._slots = asyncio.Semaphore(concurrency)
        self._wake = asyncio.Event()
        self._tasks: set[asyncio.Task] = set()

    def wake(self) -> None:
        self._wake.set()

    async def run(self) -> None:
        """Claims jobs while there are free slots; returns only when cancelled."""
        sweeper = asyncio.create_task(self._sweep_forever())
        try:
            while True:
                await self._slots.acquire()
                self._wake.clear()
                try:
                    job = await self.s.queue.claim(self.name, LEASE, MAX_ATTEMPTS)
                except Exception:
                    log.exception("worker: claim failed")
                    job = None
                if not job:
                    self._slots.release()
                    try:
                        await asyncio.wait_for(self._wake.wait(), self.idle)
                    except TimeoutError:
                        pass
                    continue
                task = asyncio.create_task(self.run_one(job))
                self._tasks.add(task)
                task.add_done_callback(self._done)
        finally:
            sweeper.cancel()
            for t in list(self._tasks):
                t.cancel()  # their leases run out and the jobs are taken up again

    def _done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        self._slots.release()

    async def run_one(self, job: Job) -> None:
        pipeline, timeout, failed = PIPELINES[job.kind]
        ctx = JobContext(self.s, job, self.name, LEASE)
        lost = asyncio.Event()
        work = asyncio.create_task(pipeline(ctx))
        beat = asyncio.create_task(self._heartbeat(ctx, work, lost))
        log.info("worker: %s job %s (try %d)", job.kind, job.id, job.attempts)
        try:
            async with asyncio.timeout(timeout):
                await asyncio.shield(work)
            job.done = job.total
            await ctx.save(status="done", error="")
        except LostLease:
            log.warning("worker: job %s was taken over", job.id)
        except JobFailed as e:
            log.error("worker: job %s failed: %s", job.id, e)
            await self._fail(ctx, e.message)
        except TimeoutError:
            work.cancel()
            log.error("worker: job %s timed out", job.id)
            await self._fail(ctx, failed)
        except asyncio.CancelledError:
            work.cancel()
            if not lost.is_set():
                raise  # shutting down: leave the job for the next worker
        except Exception:
            log.exception("worker: job %s failed (try %d)", job.id, job.attempts)
            if job.attempts < MAX_ATTEMPTS:
                await self._release(ctx)
            else:
                await self._fail(ctx, failed)
        finally:
            beat.cancel()

    async def _heartbeat(self, ctx: JobContext, work: asyncio.Task, lost: asyncio.Event) -> None:
        while not work.done():
            await asyncio.sleep(HEARTBEAT)
            try:
                ok = await self.s.queue.update(ctx.job.id, {}, worker=self.name, lease=LEASE)
            except Exception:
                log.warning("worker: heartbeat failed", exc_info=True)
                continue
            if not ok:
                lost.set()
                work.cancel()
                return

    async def _release(self, ctx: JobContext) -> None:
        """Back in the queue for another try, with what was made so far."""
        try:
            await ctx.save(status="queued", worker="", lease_until=None)
            self.wake()
        except Exception:
            log.warning("worker: release failed; the lease will run out", exc_info=True)

    async def _fail(self, ctx: JobContext, message: str) -> None:
        """Fails for good and removes the pictures already stored for it."""
        await remove_files(self.s, ctx.state.get("paths", []))
        try:
            await ctx.save(status="failed", error=message)
        except Exception:
            log.warning("worker: could not mark job %s failed", ctx.job.id, exc_info=True)


    async def _sweep_forever(self) -> None:
        while True:
            try:
                n = await sweep(self.s)
                if n:
                    log.info("worker: swept %d old jobs", n)
            except Exception:
                log.warning("worker: sweep failed", exc_info=True)
            await asyncio.sleep(SWEEP_EVERY)


async def sweep(s, keep: timedelta = KEEP_JOBS) -> int:
    """Deletes finished jobs older than keep, with their pictures unless a dream was saved from them,
    and call records older than a day."""
    await s.limits.sweep()
    swept = 0
    for _ in range(50):  # bounded, in case a delete quietly does nothing
        jobs = await s.queue.finished_before(datetime.now(timezone.utc) - keep)
        if not jobs:
            break
        for job in jobs:
            if not job.state.get("saved"):
                await remove_files(s, job.state.get("paths", []))
            await s.queue.delete(job.id)
            swept += 1
    return swept


async def main() -> None:
    from .config import load_settings
    from .services import build_services

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = build_services(load_settings())
    if not s.queue:
        raise SystemExit("no job queue: set SUPABASE_URL and SUPABASE_SERVICE_KEY")
    await Worker(s, concurrency=max(1, load_settings().workers), idle=2).run()


if __name__ == "__main__":
    asyncio.run(main())
