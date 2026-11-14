from uuid import uuid4

from .conftest import ANALYSIS, OTHER, TOKEN, auth, storyboard, wait_job

DREAM = {**ANALYSIS, "originalText": "I was flying", "type": "universal"}


def test_record_identity_survives_retries_and_booklet_attachment(api):
    client, s = api
    did, jid = str(uuid4()), str(uuid4())
    url = f"/api/v1/dreams/{did}"
    first = client.put(url, headers=auth(), json=DREAM)
    assert first.status_code == 200
    assert client.put(url, headers=auth(), json=DREAM).json()["id"] == did
    assert len(client.get("/api/v1/dreams", headers=auth()).json()["dreams"]) == 1
    s.llm.reply = storyboard(4)
    body = {"text": "I was flying", "requestId": jid}
    assert client.post("/api/v1/manga", headers=auth(), json=body).json()["id"] == jid
    wait_job(client, jid)
    assert client.post("/api/v1/manga", headers=auth(), json=body).json()["id"] == jid
    assert len(s.images.calls) == 1 and len(s.editor.calls) == 3
    attached = {**DREAM, "jobId": jid}
    saved = client.put(url + "?existing=true", headers=auth(), json=attached)
    assert saved.status_code == 200 and len(saved.json()["panels"]) == 4
    assert client.put(url, headers=auth(), json=attached).status_code == 200
    assert client.put(url, headers=auth(), json=DREAM).json()["panels"] == saved.json()["panels"]
    rows = client.get("/api/v1/dreams", headers=auth()).json()["dreams"]
    assert len(rows) == 1 and rows[0]["createdAt"] == first.json()["createdAt"]
    assert client.put(f"/api/v1/dreams/{uuid4()}", headers=auth(), json=attached).status_code == 409
    assert client.delete(url, headers=auth()).status_code == 204
    assert client.put(url + "?existing=true", headers=auth(), json=DREAM).status_code == 404


def test_recovery_ids_never_authorize_another_account(api):
    client, s = api
    did, jid = str(uuid4()), str(uuid4())
    assert client.put(f"/api/v1/dreams/{did}", json=DREAM).status_code == 401
    assert client.put(f"/api/v1/dreams/{did}", headers=auth(), json=DREAM).status_code == 200
    assert client.put(f"/api/v1/dreams/{did}", headers=auth(OTHER), json={**DREAM, "title": "stolen"}).status_code == 404
    assert client.get(f"/api/v1/dreams/{did}", headers=auth()).json()["title"] == DREAM["title"]
    s.workers = 0
    s.llm.reply = storyboard(4)
    body = {"text": "dream", "requestId": jid}
    assert client.post("/api/v1/manga", headers=auth(), json=body).status_code == 202
    assert client.post("/api/v1/manga", headers=auth(), json={**body, "text": "different"}).status_code == 409
    assert client.post("/api/v1/manga", headers=auth(OTHER), json=body).status_code == 429
    assert client.get(f"/api/v1/jobs/{jid}", headers=auth(OTHER)).status_code == 404
    assert len([j for j in s.queue.jobs.values() if j.kind != "index"]) == 1  # index jobs come with saved dreams


def test_measurement_accepts_only_content_free_events(api, caplog):
    client, _ = api
    body = {"name": "dream_saved", "eventId": str(uuid4()), "platform": "ios"}
    assert client.post("/api/v1/events", json=body).status_code == 401
    with caplog.at_level("INFO", logger="dreamlib.events"):
        assert client.post("/api/v1/events", headers=auth(), json=body).status_code == 204
    assert '"name":"dream_saved"' in caplog.text and TOKEN not in caplog.text
    assert client.post("/api/v1/events", headers=auth(), json={**body, "text": "private dream"}).status_code == 400
    assert client.post("/api/v1/events", headers=auth(), json={**body, "name": "arbitrary text"}).status_code == 400
