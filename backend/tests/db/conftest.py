"""Fixtures for the real database tests (scripts/db_test.py starts the stack and sets the env).

Without DREAMLIB_DB_TEST=1 these tests are skipped, so the ordinary `pytest -q` stays fast and offline."""
import asyncio
import os
import subprocess
import uuid

import httpx
import jwt
import pytest

ENABLED = os.environ.get("DREAMLIB_DB_TEST") == "1"


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/db" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.db)
            if not ENABLED:
                item.add_marker(pytest.mark.skip(reason="real database tests: run scripts/db_test.py"))


def sql(query: str) -> str:
    """Runs SQL as postgres in the test database and returns the unaligned output."""
    res = subprocess.run(
        ["docker", "compose", "-f", os.environ["DREAMLIB_DB_COMPOSE"], "exec", "-T", "db",
         "psql", "-U", "postgres", "-d", "postgres", "-At", "-v", "ON_ERROR_STOP=1", "-c", query],
        capture_output=True, text=True, encoding="utf-8",
    )
    if res.returncode:
        raise SqlError(res.stderr.strip())
    return res.stdout.strip()


class SqlError(Exception):
    pass


class StripRestPrefix(httpx.AsyncBaseTransport):
    """The app calls Supabase at /rest/v1/...; plain PostgREST serves the same API at /."""

    def __init__(self):
        self.inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/rest/v1")
        request.url = request.url.copy_with(path=path or "/")
        return await self.inner.handle_async_request(request)


def service_key() -> str:
    return jwt.encode({"role": "service_role", "iss": "dreamlib-db-test"}, os.environ["DREAMLIB_DB_SECRET"], algorithm="HS256")


@pytest.fixture
def sb():
    from app.store.supabase import Supabase

    return Supabase(os.environ["DREAMLIB_DB_REST"], service_key(), allow_http=True, transport=StripRestPrefix())


@pytest.fixture
def user():
    """A fresh auth user; its jobs, dreams and usage rows go with it."""
    uid = str(uuid.uuid4())
    sql(f"insert into auth.users (id, email) values ('{uid}', '{uid}@test.local')")
    yield uid
    sql(f"delete from auth.users where id = '{uid}'")


@pytest.fixture
def dream(user):
    did = str(uuid.uuid4())
    sql(f"insert into public.dreams (id, user_id, title, original_text) values ('{did}', '{user}', 'test', 'test')")
    return did


@pytest.fixture(autouse=True)
def clean_queue():
    """claim_job takes the oldest job of anyone; each test starts with an empty queue."""
    if ENABLED:
        sql("delete from public.jobs")
    yield


_loop = asyncio.new_event_loop()  # one loop for the session: the app's HTTP clients live on one loop


def run(coro):
    return _loop.run_until_complete(coro)
