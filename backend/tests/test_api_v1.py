"""S1: the API lives under /api/v1; the old unversioned paths still answer, in place and marked deprecated."""
from .conftest import auth
from .test_dreams import DREAM


def test_v1_paths_answer_without_a_deprecation_mark(api):
    client, _ = api
    res = client.post("/api/v1/dreams", headers=auth(), json=DREAM)
    assert res.status_code == 201 and "deprecation" not in res.headers
    got = client.get(f"/api/v1/dreams/{res.json()['id']}", headers=auth())
    assert got.status_code == 200 and got.json()["id"] == res.json()["id"]


def test_old_paths_are_served_in_place_and_marked(api):
    client, _ = api
    res = client.post("/api/dreams", headers=auth(), json=DREAM)  # no redirect: the body arrives as sent
    assert res.status_code == 201 and res.headers["deprecation"] == "true"
    dream_id = res.json()["id"]
    got = client.get(f"/api/dreams/{dream_id}?x=1", headers=auth())
    assert got.status_code == 200 and got.headers["link"] == f'</api/v1/dreams/{dream_id}>; rel="successor-version"'
    assert client.get("/api/v1/dreams", headers=auth()).json()["dreams"][0]["id"] == dream_id


def test_old_audio_uploads_keep_the_audio_limit(api):
    client, s = api
    for url in ("/api/transcribe", "/api/v1/transcribe"):
        res = client.post(url, headers={**auth(), "Content-Type": "audio/webm"}, content=b"x" * (2 << 20))
        assert res.status_code == 200, url  # above the 1 MB JSON limit, under the audio limit


def test_the_schema_lists_only_v1(api):
    client, _ = api
    paths = client.get("/openapi.json").json()["paths"]
    assert paths and all(p.startswith("/api/v1/") for p in paths if p != "/healthz")
    assert client.get("/healthz").status_code == 200 and "deprecation" not in client.get("/healthz").headers


def test_unknown_paths_stay_unknown(api):
    client, _ = api
    assert client.get("/api/nothing", headers=auth()).status_code == 404
    assert client.get("/api/v1/nothing", headers=auth()).status_code == 404
    assert client.get("/apix/dreams", headers=auth()).status_code == 404
