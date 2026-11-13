import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import sse
from app.providers import openrouter
from app.providers.fake import FakeLLM
from app.providers.openrouter import TASKS, OpenRouter

MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "uçan bir koala gördüm"}]


def chunk(text="", **extra) -> str:
    body = {"model": "m/one", "choices": [{"delta": {"content": text}}] if text else [], **extra}
    return "data: " + json.dumps(body, ensure_ascii=False) + "\n\n"


def client(*answers, routes=None):
    """answers: (status, sse text) per request in order."""
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((json.loads(req.content), req.extensions["timeout"]["read"]))
        status, text = answers[len(seen) - 1]
        return httpx.Response(status, content=text.encode(), headers={"content-type": "text/event-stream"})

    llm = OpenRouter("key", "default/model", routes)
    llm.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm, seen


async def collect(gen):
    return [x async for x in gen]


def test_stream_yields_pieces_skips_keepalives_and_stops_at_done():
    body = ": OPENROUTER PROCESSING\n\n" + chunk("Uçan ") + chunk("koala") + chunk(usage={"total_tokens": 9}) \
        + "data: [DONE]\n\n" + chunk("after done")
    llm, seen = client((200, body), routes={"interpret": ("m/one", ("m/two",))})
    assert asyncio.run(collect(llm.stream(MESSAGES, task="interpret"))) == ["Uçan ", "koala"]
    sent, timeout = seen[0]
    assert sent["stream"] is True and sent["models"] == ["m/one", "m/two"] and timeout == TASKS["interpret"]


def test_stream_retries_once_before_the_first_byte(monkeypatch):
    monkeypatch.setattr(openrouter, "RETRY_AFTER", 0)
    llm, seen = client((503, "busy"), (200, chunk("tamam") + "data: [DONE]\n\n"))
    assert asyncio.run(collect(llm.stream(MESSAGES, task="interpret"))) == ["tamam"]
    assert len(seen) == 2


def test_stream_raises_on_a_client_error_and_on_an_error_mid_stream():
    llm, _ = client((400, "bad"))
    with pytest.raises(RuntimeError):
        asyncio.run(collect(llm.stream(MESSAGES, task="interpret")))
    llm, _ = client((200, chunk("yarım ") + "data: " + json.dumps({"error": {"message": "provider down"}}) + "\n\n"))
    got = []

    async def run():
        async for piece in llm.stream(MESSAGES, task="interpret"):
            got.append(piece)

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert got == ["yarım "]  # what came before the failure was delivered


def test_fake_stream_spells_out_the_sample_interpretation():
    pieces = asyncio.run(collect(FakeLLM().stream(MESSAGES)))
    assert len(pieces) > 3 and "".join(pieces).startswith("Bu, yerel deneme")


def test_event_format_and_unknown_kinds():
    assert sse.event("text", {"text": "ç"}) == 'event: text\ndata: {"text":"ç"}\n\n'.encode()
    with pytest.raises(ValueError):
        sse.event("chat")


def parse(raw: str) -> list[tuple[str, dict]]:
    out = []
    for block in raw.strip().split("\n\n"):
        kind, data = block.split("\n")
        out.append((kind.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return out


def app_with(events):
    app = FastAPI()

    @app.get("/s")
    async def s():
        return sse.sse_response(events())

    return TestClient(app)


def test_response_streams_events_and_ends_with_done():
    async def events():
        yield "title", {"title": "Koala"}
        async for e in sse.text_events(FakeLLM().stream(MESSAGES)):
            yield e

    res = app_with(events).get("/s")
    assert res.headers["content-type"].startswith("text/event-stream") and res.headers["x-accel-buffering"] == "no"
    got = parse(res.text)
    assert got[0] == ("title", {"title": "Koala"}) and got[-1] == ("done", {})
    assert {k for k, _ in got[1:-1]} == {"text"}


def test_a_failure_after_the_first_event_becomes_an_error_event():
    async def events():
        yield "text", {"text": "yarım"}
        raise RuntimeError("model gone")

    res = app_with(events).get("/s")
    assert res.status_code == 200
    assert parse(res.text) == [("text", {"text": "yarım"}), ("error", {"message": sse.FAILED})]
