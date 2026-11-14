"""What happens to a dream after it is saved: its interpretation row is tied to it (M3) and the index job
is queued for this revision (M4). Neither may fail the save; problems are logged."""
import logging

from .store.jobstore import Busy, Duplicate

log = logging.getLogger("dreamlib")


async def after_save(s, user_id: str, dream_id: str, revision: int, analysis_id: str = "") -> None:
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
