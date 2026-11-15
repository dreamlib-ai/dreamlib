"""R2: take everything with you, or delete the account and everything in it (in-memory store)."""
from .conftest import OTHER, auth
from .test_dreams import DREAM


def test_the_export_holds_every_dream_and_consent_as_a_file(api):
    client, s = api
    saved = client.post("/api/v1/dreams", headers=auth(), json={**DREAM, "visibility": "public"}).json()
    client.post("/api/v1/dreams", headers=auth(OTHER), json=DREAM)
    res = client.get("/api/v1/account/export", headers=auth())
    assert res.status_code == 200 and res.headers["content-disposition"].startswith('attachment; filename="dreamlib-')
    data = res.json()
    assert [d["id"] for d in data["dreams"]] == [saved["id"]]  # never someone else's
    assert data["dreams"][0]["originalText"] == DREAM["originalText"] and data["profile"]["id"]
    assert sorted(r["scope"] for r in data["consents"]) == ["collective", "public"]
    assert {"magazines", "analyses", "exportedAt"} <= set(data)
    assert client.get("/api/v1/account/export").status_code == 401


def test_deleting_the_account_takes_everything_and_needs_the_word(api):
    client, s = api
    client.post("/api/v1/dreams", headers=auth(), json={**DREAM, "visibility": "public"})
    kept = client.post("/api/v1/dreams", headers=auth(OTHER), json=DREAM).json()
    assert client.request("DELETE", "/api/v1/account", headers=auth(), json={}).status_code == 400
    assert client.request("DELETE", "/api/v1/account", headers=auth(), json={"confirm": "yes"}).status_code == 400
    assert client.request("DELETE", "/api/v1/account", headers=auth(), json={"confirm": "delete"}).status_code == 204
    gone = client.get("/api/v1/dreams", headers=auth())  # the token still verifies, the account does not exist
    assert gone.status_code == 401 and gone.json()["code"] == "auth_invalid" and not s.store.consents
    assert client.post("/api/v1/analyze", headers=auth(), json={"text": "Uçuyordum."}).status_code == 401
    assert client.get(f"/api/v1/dreams/{kept['id']}", headers=auth(OTHER)).status_code == 200  # others untouched
