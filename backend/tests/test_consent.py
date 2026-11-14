"""R1: per-dream consent tiers and the ledger, on the in-memory store."""
from uuid import uuid4

from .conftest import OTHER, auth
from .test_contract import check
from .test_dreams import DREAM


def active(s, dream_id):
    return sorted((r["scope"], r["version"]) for r in s.store.consents if r["dream_id"] == dream_id and not r["withdrawn"])


def test_a_new_dream_takes_the_onboarding_choice_into_the_ledger(api):
    client, s = api
    saved = client.post("/api/v1/dreams", headers=auth(), json={**DREAM, "visibility": "public"}).json()
    assert saved["visibility"] == "public"
    assert active(s, saved["id"]) == [("collective", "onboarding@1"), ("public", "onboarding@1")]
    plain = client.post("/api/v1/dreams", headers=auth(), json=DREAM).json()
    assert plain["visibility"] == "private" and active(s, plain["id"]) == []
    assert client.post("/api/v1/dreams", headers=auth(), json={**DREAM, "visibility": "friends"}).status_code == 400


def test_tiers_change_only_through_the_consent_endpoint_with_the_current_wording(api):
    client, s = api
    saved = client.put(f"/api/v1/dreams/{uuid4()}", headers=auth(), json=DREAM).json()  # a client-made id, saved again below
    url = f"/api/v1/dreams/{saved['id']}/consent"
    version = client.get("/api/v1/consent", headers=auth()).json()["textVersion"]
    assert version == "consent@1"
    assert client.put(url, headers=auth(), json={"tier": "collective"}).status_code == 409  # wording not shown
    assert client.put(url, headers=auth(), json={"tier": "collective", "textVersion": "consent@0"}).status_code == 409
    assert client.put(url, headers=auth(OTHER), json={"tier": "collective", "textVersion": version}).status_code == 404
    assert client.put(url, headers=auth(), json={"tier": "everyone", "textVersion": version}).status_code == 400
    res = client.put(url, headers=auth(), json={"tier": "public", "textVersion": version})
    assert res.status_code == 200 and res.json() == {"tier": "public", "textVersion": version}
    spec = client.app.openapi()
    check(spec, spec["components"]["schemas"]["ConsentOut"], res.json())
    assert active(s, saved["id"]) == [("collective", version), ("public", version)]

    # a later save cannot lower or raise the tier
    again = client.put(f"/api/v1/dreams/{saved['id']}", headers=auth(), json={**DREAM, "visibility": "private"}).json()
    assert again["visibility"] == "public"

    assert client.put(url, headers=auth(), json={"tier": "collective", "textVersion": version}).json()["tier"] == "collective"
    assert active(s, saved["id"]) == [("collective", version)]
    assert client.put(url, headers=auth(), json={"tier": "private"}).json()["tier"] == "private"
    assert active(s, saved["id"]) == [] and len(s.store.consents) == 2  # withdrawals stay in the ledger
    assert client.get(f"/api/v1/dreams/{saved['id']}", headers=auth()).json()["visibility"] == "private"
