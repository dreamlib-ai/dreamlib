import asyncio
import json

import httpx
import pytest

from app.config import llm_routes
from app.providers.openrouter import TASKS, OpenRouter


def client(routes=None, model="default/model"):
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((json.loads(req.content), req.extensions["timeout"]["read"]))
        return httpx.Response(200, json={"model": "x", "choices": [{"message": {"content": "ok"}}]})

    llm = OpenRouter("key", model, routes)
    llm.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm, seen


def ask(llm, task):
    return asyncio.run(llm.chat([{"role": "user", "content": "hi"}], task=task))


def test_task_without_its_own_model_uses_the_default_and_its_timeout():
    llm, seen = client()
    assert ask(llm, "clean") == "ok"
    body, timeout = seen[0]
    assert body["model"] == "default/model" and "models" not in body
    assert timeout == TASKS["clean"]


def test_task_model_and_fallbacks_go_as_an_ordered_list():
    llm, seen = client({"interpret": ("good/model", ("backup/a", "good/model", "backup/b"))})
    ask(llm, "interpret")
    body, timeout = seen[0]
    assert body["models"] == ["good/model", "backup/a", "backup/b"] and "model" not in body
    assert timeout == TASKS["interpret"]
    ask(llm, "storyboard")  # other tasks are untouched
    assert seen[1][0]["model"] == "default/model"


def test_fallbacks_alone_follow_the_default_model():
    llm, _ = client({"extract": ("", ("backup/a",))})
    assert llm.models_for("extract") == ["default/model", "backup/a"]


def test_unknown_task_and_missing_model_fail_before_any_request():
    llm, seen = client(model="")
    with pytest.raises(ValueError):
        ask(llm, "summarize")
    with pytest.raises(RuntimeError):
        ask(llm, "clean")
    assert seen == [] and not llm.enabled
    assert OpenRouter("key", "", {"clean": ("only/clean", ())}).enabled


def test_routes_are_read_from_the_environment():
    env = {
        "OPENROUTER_MODEL_CLEAN": " cheap/model ",
        "OPENROUTER_FALLBACK_INTERPRET": "a/one, b/two,,",
        "OPENROUTER_MODEL_NOPE": "ignored/model",
    }.get
    assert llm_routes(env) == {"clean": ("cheap/model", ()), "interpret": ("", ("a/one", "b/two"))}


def test_provider_status_decides_the_error_class(monkeypatch):
    monkeypatch.setattr("app.providers.openrouter.RETRY_AFTER", 0)
    from app.providers.errors import ProviderError, is_transient

    for status, transient in [(503, True), (400, False)]:
        llm = OpenRouter("key", "m")
        llm.http = httpx.AsyncClient(transport=httpx.MockTransport(lambda req, st=status: httpx.Response(st, text="no")))
        with pytest.raises(ProviderError) as err:
            asyncio.run(llm.chat([], task="clean"))
        assert err.value.status == status and is_transient(err.value) is transient
