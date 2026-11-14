"""S3: real answers match the OpenAPI schema the TypeScript client is generated from (app/contract.py).

The checker follows $ref, objects (required keys present, no undocumented keys), arrays, nullable unions
and enums, so a route that drifts from its documented shape fails here before the web app sees it."""
import pytest

from .conftest import auth, storyboard, wait_job
from .test_dreams import DREAM


def check(spec: dict, schema: dict, value, where: str = "$") -> None:
    if "$ref" in schema:
        return check(spec, spec["components"]["schemas"][schema["$ref"].rsplit("/", 1)[1]], value, where)
    if "anyOf" in schema:
        errors = []
        for option in schema["anyOf"]:
            try:
                return check(spec, option, value, where)
            except AssertionError as e:
                errors.append(str(e))
        raise AssertionError(f"{where}: none of anyOf fits: {errors}")
    if "enum" in schema:
        assert value in schema["enum"], f"{where}: {value!r} not in {schema['enum']}"
    kind = schema.get("type")
    if kind == "null":
        assert value is None, f"{where}: expected null"
    elif kind == "object":
        assert isinstance(value, dict), f"{where}: expected object"
        props = schema.get("properties", {})
        missing = [k for k in schema.get("required", []) if k not in value]
        extra = [k for k in value if k not in props] if props else []
        assert not missing and not extra, f"{where}: missing {missing}, undocumented {extra}"
        for k, v in value.items():
            if k in props:
                check(spec, props[k], v, f"{where}.{k}")
    elif kind == "array":
        assert isinstance(value, list), f"{where}: expected array"
        for i, v in enumerate(value):
            check(spec, schema.get("items", {}), v, f"{where}[{i}]")
    elif kind == "string":
        assert isinstance(value, str), f"{where}: expected string"
    elif kind == "integer":
        assert isinstance(value, int) and not isinstance(value, bool), f"{where}: expected integer"
    elif kind == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{where}: expected number"
    elif kind == "boolean":
        assert isinstance(value, bool), f"{where}: expected boolean"


@pytest.fixture
def contract(api):
    client, s = api
    spec = client.app.openapi()
    ops = {op["operationId"]: op for ops in spec["paths"].values() for op in ops.values()}

    def answer(op_id: str, res):
        code = str(res.status_code)
        assert code in ops[op_id]["responses"], f"{op_id}: undocumented status {code}: {res.text[:200]}"
        content = ops[op_id]["responses"][code].get("content", {}).get("application/json")
        if content and content.get("schema"):
            check(spec, content["schema"], res.json(), op_id)
        return res.json() if res.content else None

    return client, s, answer


def test_every_json_answer_matches_its_schema(contract):
    client, s, answer = contract
    h = auth()
    answer("clean", client.post("/api/v1/clean", headers=h, json={"text": "ormanda uçtum"}))
    analysis = answer("analyze", client.post("/api/v1/analyze", headers=h, json={"text": "Ormanda uçtum."}))
    answer("transcribe", client.post("/api/v1/transcribe", headers={**h, "Content-Type": "audio/webm"}, content=b"audio"))
    dream = answer("save_dream", client.post("/api/v1/dreams", headers=h, json={**DREAM, **analysis}))
    answer("get_dream", client.get(f"/api/v1/dreams/{dream['id']}", headers=h))
    answer("list_dreams", client.get("/api/v1/dreams", headers=h))
    answer("dream_status", client.get(f"/api/v1/dreams/{dream['id']}/status", headers=h))
    edited = answer("edit_journal", client.patch(f"/api/v1/dreams/{dream['id']}/journal", headers=h,
                                                 json={"revision": dream["revision"], "favorite": True,
                                                       "classification": {"genres": ["fantasy"]}}))
    assert edited["journal"]["classification"]["genres"] == ["fantasy"]
    answer("put_dream", client.put("/api/v1/dreams/7d9f5c8e-4c55-4d6b-9f3b-2b1f0c4a6e11", headers=h, json=DREAM))
    answer("get_profile", client.get("/api/v1/profile", headers=h))
    answer("update_profile", client.patch("/api/v1/profile", headers=h, json={"revision": 0, "presetId": "ink"}))
    answer("event", client.post("/api/v1/events", headers=h,
                                json={"name": "dream_saved", "eventId": "0f8fad5b-d9cb-469f-a165-70867728950e", "platform": "desktop"}))
    answer("delete_dream", client.delete(f"/api/v1/dreams/{dream['id']}", headers=h))


def test_job_answers_match_while_running_and_done(contract):
    client, s, answer = contract
    s.llm.reply = storyboard(4)
    job_id = answer("start_manga", client.post("/api/v1/manga", headers=auth(), json={"text": "Uçtum.", "panels": 4}))["id"]
    answer("get_job", client.get(f"/api/v1/jobs/{job_id}", headers=auth()))  # running, maybe with an estimate
    wait_job(client, job_id)
    done = answer("get_job", client.get(f"/api/v1/jobs/{job_id}", headers=auth()))
    assert done["status"] == "done" and done["panels"][0]["url"]
    answer("redo_panel", client.post(f"/api/v1/jobs/{job_id}/panels/1/redo", headers=auth()))
    answer("start_images", client.post("/api/v1/images", headers=auth(), json={"prompt": "ay", "style": "manga", "count": 1}))
