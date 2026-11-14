"""What happens to a dream after it is saved: its interpretation row is tied to it (M3), the index job is
queued for this revision (M4) and the magazine job for these panels (G4). None may fail the save; problems
are logged."""
import hashlib
import logging

from .store.jobstore import Busy, Duplicate

log = logging.getLogger("dreamlib")


async def after_save(s, user_id: str, dream_id: str, revision: int, analysis_id: str = "",
                     panels: list[str] | None = None) -> None:
    if analysis_id and s.analyses:
        try:
            if not await s.analyses.attach(user_id, analysis_id, dream_id):
                log.info("analyses: %s not attached (unknown, foreign or already attached)", analysis_id)
        except Exception:
            log.warning("analyses: could not attach %s to %s", analysis_id, dream_id, exc_info=True)
    if s.queue is None:
        return
    try:
        await s.queue.create(user_id, "index", {"dreamId": dream_id, "revision": revision}, 1,
                             dream_id=dream_id, dedupe_key=f"{dream_id}:{revision}")
        s.wake()
    except (Duplicate, Busy):
        pass  # this revision is already queued or done
    except Exception:
        log.warning("index: could not queue %s", dream_id, exc_info=True)
    if panels is not None:
        await queue_magazine(s, user_id, dream_id, revision, panels)


async def queue_magazine(s, user_id: str, dream_id: str, revision: int, panels: list[str]) -> None:
    """Lays the magazine out again for this revision and these pictures; a dream without panels loses it."""
    if s.queue is None or getattr(s, "magazines", None) is None:
        return
    key = hashlib.sha256("|".join(panels).encode()).hexdigest()[:16]
    try:
        await s.queue.create(user_id, "magazine", {"dreamId": dream_id}, 1, dream_id=dream_id,
                             dedupe_key=f"{dream_id}:{revision}:{key}")
        s.wake()
    except (Duplicate, Busy):
        pass
    except Exception:
        log.warning("magazine: could not queue %s", dream_id, exc_info=True)
