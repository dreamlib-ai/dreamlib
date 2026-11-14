"""Job kinds live here, not in a database check: a new kind is one entry in KINDS.
The queue refuses a kind that is not listed; the worker fails such a job instead of crashing."""
from dataclasses import dataclass
from typing import Awaitable, Callable

from . import image, index, magazine, manga
from .context import JobContext


@dataclass(frozen=True)
class Kind:
    run: Callable[[JobContext], Awaitable[None]]
    timeout: float  # seconds for one try
    failed: str  # what the user reads when the job gives up
    exclusive: bool = True  # at most one exclusive job per user is queued or running (paid drawing)
    priority: int = 0  # higher goes first; jobs a user is waiting on outrank background work


KINDS: dict[str, Kind] = {
    "manga": Kind(manga.run, manga.MANGA_TIMEOUT, manga.FAILED, priority=10),
    "image": Kind(image.run, 3 * 60, image.FAILED, priority=10),
    "index": Kind(index.run, index.TIMEOUT, index.FAILED, exclusive=False),  # background; never blocks the user
    "magazine": Kind(magazine.run, magazine.TIMEOUT, magazine.FAILED, exclusive=False),  # lays out saved panels; free
}

UNKNOWN = "bu iş türü artık desteklenmiyor"


class UnknownKind(ValueError):
    """A job kind that has no entry in KINDS."""


def check(kind: str) -> Kind:
    if kind not in KINDS:
        raise UnknownKind(kind)
    return KINDS[kind]
