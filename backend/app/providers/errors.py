"""How a provider call failed, decided where the call is made. The worker only applies it."""
import asyncio

import httpx


class ProviderError(RuntimeError):
    """A provider answered badly. status is the HTTP status, or 0 for a timeout or a lost connection."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status

    @property
    def transient(self) -> bool:
        return self.status == 0 or self.status == 408 or self.status == 429 or self.status >= 500


def is_transient(exc: BaseException) -> bool:
    """True when waiting and trying again may help. Follows the cause chain; unknown errors count as
    transient, so a bug costs a few bounded retries rather than a lost job."""
    seen = 0
    while exc is not None and seen < 10:
        if isinstance(exc, ProviderError):
            return exc.transient
        if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, asyncio.TimeoutError)):
            return True
        exc, seen = exc.__cause__, seen + 1
    return True
