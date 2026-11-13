"""Job kinds live here, not in a database check: a new kind is one entry in KINDS.
The queue refuses a kind that is not listed; the worker fails such a job instead of crashing."""
from dataclasses import dataclass
from typing import Awaitable, Callable

from . import image, manga
from .context import JobContext


@dataclass(frozen=True)
class Kind:
    run: Callable[[JobContext], Awaitable[None]]
    timeout: float  # seconds for one try
    failed: str  # what the user reads when the job gives up


KINDS: dict[str, Kind] = {
    "manga": Kind(manga.run, manga.MANGA_TIMEOUT, manga.FAILED),
    "image": Kind(image.run, 3 * 60, image.FAILED),
}

UNKNOWN = "bu iş türü artık desteklenmiyor"


class UnknownKind(ValueError):
    """A job kind that has no entry in KINDS."""


def check(kind: str) -> Kind:
    if kind not in KINDS:
        raise UnknownKind(kind)
    return KINDS[kind]
