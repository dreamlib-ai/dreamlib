import asyncio
import json

import httpx
import pytest

from app.providers import openrouter
from app.providers.fake import FakeLLM
from app.providers.openrouter import EMBED_ENDPOINT, TASKS, OpenRouter


def client(respond, routes=None, model="default/model"):
    """An OpenRouter whose requests go to respond(body) -> (status, json); returns it and the requests seen."""
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        seen.append((str(req.url), body, req.extensions["timeout"]["read"]))
        status, out = respond(body)
        return httpx.Response(status, json=out)

    llm = OpenRouter("key", model, routes)
    llm.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm, seen


def vectors_for(body, dims=3, model="emb/model"):
    # answered out of order on purpose: the client must sort by index
    data = [{"index": i, "embedding": [float(i)] * dims} for i in range(len(body["input"]))]
    return 200, {"model": model, "data": list(reversed(data)), "usage": {"total_tokens": 5}}


def test_embed_uses_its_task_model_endpoint_and_timeout_and_keeps_text_order():
    llm, seen = client(vectors_for, {"embed": ("emb/model", ())})
    out = asyncio.run(llm.embed(["a", "b", "c"]))
    url, body, timeout = seen[0]
    assert url == EMBED_ENDPOINT and timeout == TASKS["embed"]
    assert body == {"model": "emb/model", "input": ["a", "b", "c"], "encoding_format": "float"}
    assert out.model == "emb/model" and out.dims == 3
    assert [v[0] for v in out.vectors] == [0.0, 1.0, 2.0]


def test_embed_never_falls_back_to_another_model():
    llm, seen = client(vectors_for, {"embed": ("emb/main", ("emb/other",))})
    asyncio.run(llm.embed(["a"]))
    assert seen[0][1]["model"] == "emb/main" and "models" not in seen[0][1]


def test_embed_batches_long_inputs(monkeypatch):
    monkeypatch.setattr(openrouter, "EMBED_BATCH", 2)
    llm, seen = client(vectors_for)
    out = asyncio.run(llm.embed(["a", "b", "c", "d", "e"]))
    assert [len(b["input"]) for _, b, _ in seen] == [2, 2, 1]
    assert len(out.vectors) == 5 and out.model == "emb/model"


def test_embed_without_texts_makes_no_request():
    llm, seen = client(vectors_for)
    out = asyncio.run(llm.embed([]))
    assert seen == [] and out.vectors == [] and out.dims == 0


@pytest.mark.parametrize("answer", [
    {"data": [{"index": 0, "embedding": [1.0]}]},  # fewer vectors than texts
    {"data": [{"index": 0, "embedding": []}, {"index": 1, "embedding": [1.0]}]},  # empty vector
    {"data": [{"index": 0, "embedding": ["x"]}, {"index": 1, "embedding": [1.0]}]},  # not numbers
    {"data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [1.0, 2.0]}]},  # sizes differ
])
def test_embed_rejects_malformed_answers(answer):
    llm, _ = client(lambda body: (200, answer))
    with pytest.raises(RuntimeError):
        asyncio.run(llm.embed(["a", "b"]))


def test_embed_retries_once_on_a_rate_limit(monkeypatch):
    monkeypatch.setattr(openrouter, "RETRY_AFTER", 0)
    calls = []

    def respond(body):
        calls.append(1)
        return (429, {"error": "slow down"}) if len(calls) == 1 else vectors_for(body)

    llm, _ = client(respond)
    assert asyncio.run(llm.embed(["a"])).dims == 3 and len(calls) == 2


def test_embed_does_not_retry_a_client_error():
    llm, seen = client(lambda body: (400, {"error": "bad input"}))
    with pytest.raises(RuntimeError):
        asyncio.run(llm.embed(["a"]))
    assert len(seen) == 1


def test_embed_needs_a_model():
    llm, seen = client(vectors_for, model="")
    with pytest.raises(RuntimeError):
        asyncio.run(llm.embed(["a"]))
    assert seen == []


def test_fake_embeddings_are_stable_unit_vectors():
    out = asyncio.run(FakeLLM().embed(["uçan koala", "uçan koala", "deniz"]))
    assert out.model == "fake" and out.dims == 8
    assert out.vectors[0] == out.vectors[1] != out.vectors[2]
    assert abs(sum(x * x for x in out.vectors[0]) - 1) < 1e-9
