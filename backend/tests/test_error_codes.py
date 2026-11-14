"""S2: every error answer carries a machine code from one registry, and docs/api.md lists them all."""
from pathlib import Path

import pytest

from app.errors import CODES, ApiError

from .conftest import auth
from .test_dreams import DREAM


def test_every_code_is_documented():
    doc = (Path(__file__).parents[2] / "docs" / "api.md").read_text(encoding="utf-8")
    assert [c for c in CODES if f"`{c}`" not in doc] == []


def test_a_code_outside_the_registry_is_a_bug():
    with pytest.raises(ValueError):
        ApiError(400, "x", "made_up")
    assert ApiError(503, "x").code == "service_off" and ApiError(418, "x").code == "invalid_request"


def code(res):
    return res.status_code, res.json()["code"]


def test_framework_errors_have_codes(api):
    client, _ = api
    assert code(client.get("/api/v1/dreams")) == (401, "auth_required")
    assert code(client.get("/api/v1/nothing", headers=auth())) == (404, "not_found")
    assert code(client.post("/api/v1/dreams", headers=auth(), json={"originalText": 5})) == (400, "invalid_request")
    big = client.post("/api/v1/dreams", headers={**auth(), "Content-Type": "application/json"}, content=b"x" * (2 << 20))
    assert code(big) == (413, "too_large")


def test_a_stale_revision_is_a_revision_conflict(api):
    client, _ = api
    dream = client.post("/api/v1/dreams", headers=auth(), json=DREAM).json()
    patch = {"revision": dream["revision"], "title": "Yeni"}
    assert client.patch(f"/api/v1/dreams/{dream['id']}/journal", headers=auth(), json=patch).status_code == 200
    stale = client.patch(f"/api/v1/dreams/{dream['id']}/journal", headers=auth(), json=patch)
    assert code(stale) == (409, "revision_conflict")
