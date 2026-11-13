"""Server-sent events for answers that are written while the user waits (docs/istemci.md, Akışlı yorum).

An event is a kind and a JSON object. The kinds are fixed so the client can draw each one:
title, entity (node id, label, icon url), text (a piece of a sentence), emotion, section (rüya,
semboller, sende, başkalarında), done; and error when the stream cannot go on. Once the first byte is
out the HTTP status is 200 whatever happens, so a failure becomes an `error` event, and the client
reads the saved result instead of waiting on the connection."""
import json
import logging
from collections.abc import AsyncIterable, AsyncIterator

from fastapi.responses import StreamingResponse

log = logging.getLogger("dreamlib")

KINDS = frozenset({"title", "entity", "text", "emotion", "section", "done", "error"})
FAILED = "yorum yarıda kaldı; kaydedilen sonuç birazdan görünür"


def event(kind: str, data: dict | None = None) -> bytes:
    if kind not in KINDS:
        raise ValueError(f"sse: unknown event kind {kind!r}")
    body = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
    return f"event: {kind}\ndata: {body}\n\n".encode()


async def text_events(pieces: AsyncIterable[str]) -> AsyncIterator[tuple[str, dict]]:
    """A model's text stream as `text` events; empty pieces are dropped."""
    async for piece in pieces:
        if piece:
            yield "text", {"text": piece}


async def encode(events: AsyncIterable[tuple[str, dict]]) -> AsyncIterator[bytes]:
    """Events as SSE bytes, ending with `done`; an exception ends the stream with `error` instead."""
    try:
        async for kind, data in events:
            yield event(kind, data)
    except Exception:
        log.exception("sse: stream failed")
        yield event("error", {"message": FAILED})
        return
    yield event("done")


def sse_response(events: AsyncIterable[tuple[str, dict]]) -> StreamingResponse:
    return StreamingResponse(encode(events), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",  # proxies must not hold pieces back
    })
