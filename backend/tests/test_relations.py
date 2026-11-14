"""BG1: dream ↔ dream relations, scored without a model, weak ones dropped."""
import time
from datetime import date

import pytest

from app.engine.relations import TOP, DreamNodes, Node, relate
from app.store.analyses import MemoryAnalyses
from app.store.entities import MemoryEntities
from app.store.graph import MemoryGraph

from .conftest import auth, make_client
from .test_contract import check
from .test_dreams import DREAM

SEA = Node("e-sea", "symbol", "sym.deniz", "deniz")
MOM = Node("e-mom", "character", "chr.annem", "annem")
HOUSE = Node("e-house", "place", "plc.ev", "ev")
FEAR = Node("e-fear", "emotion", "hvdc.apprehension", "Korku ve kaygı")
JOY = Node("e-joy", "emotion", "hvdc.happiness", "Mutluluk")
LUCID = Node("e-lucid", "theme", "experience.lucid", "Bilinçli rüya")


def dream(id_, day, *nodes):
    return DreamNodes(id_, date(2026, 11, day), {n.id: n for n in nodes})


def by(edges, relation):
    return {(e.source, e.target): e for e in edges if e.relation == relation}


def test_shared_content_concept_and_emotion_are_separate_links():
    corpus = [dream("a", 1, SEA, MOM, FEAR, LUCID), dream("b", 20, SEA, MOM, FEAR, LUCID), dream("c", 25, HOUSE, JOY)]
    edges = relate("a", corpus)
    content = by(edges, "shares_content")[("a", "b")]
    assert content.weight == 1.0 and {s["key"] for s in content.evidence["shared"]} == {"sym.deniz", "chr.annem"}
    assert ("a", "b") in by(edges, "shares_concept") and ("a", "b") in by(edges, "shares_emotion")
    assert not any("c" in (e.source, e.target) for e in edges)  # nothing in common, far apart: floats free
    assert not by(edges, "near_in_time")


def test_a_weak_overlap_is_not_kept():
    many = [Node(f"e{i}", "symbol", f"sym.s{i}", f"s{i}") for i in range(8)]
    corpus = [dream("a", 1, SEA, *many), dream("b", 20, SEA, HOUSE, MOM)]
    assert not by(relate("a", corpus), "shares_content")  # one shared symbol out of eleven


def test_rare_nodes_weigh_more_than_common_ones():
    corpus = [dream("a", 1, SEA, HOUSE), dream("b", 20, SEA, MOM), dream("c", 22, HOUSE, MOM)]
    corpus += [dream(f"x{i}", 27, HOUSE) for i in range(6)]  # the house is in almost every dream
    edges = by(relate("a", corpus), "shares_content")
    weak = edges.get(("a", "c"))
    assert ("a", "b") in edges and (weak is None or weak.weight < edges[("a", "b")].weight)


def test_time_links_only_close_dreams_and_sorts_ids():
    corpus = [dream("m", 10), dream("k", 11), dream("z", 13), dream("q", 20)]
    edges = by(relate("m", corpus), "near_in_time")
    assert set(edges) == {("k", "m"), ("m", "z")}  # symmetric: source sorts first; 10 days apart is dropped
    assert edges[("k", "m")].weight > edges[("m", "z")].weight and edges[("k", "m")].evidence == {"days": 1}


def test_each_type_keeps_only_the_strongest_few():
    corpus = [dream("a", 1)] + [dream(f"b{i}", 1 + (i % 2)) for i in range(10)]
    assert len(by(relate("a", corpus), "near_in_time")) == TOP["near_in_time"]


def test_an_unknown_or_lonely_dream_has_no_links():
    assert relate("nope", [dream("a", 1)]) == [] and relate("a", [dream("a", 1)]) == []


@pytest.fixture
def brain_api(monkeypatch):
    monkeypatch.setattr("app.worker.BACKOFF", (0, 0, 0))
    entities = MemoryEntities()
    client, s = make_client(analyses=MemoryAnalyses(), entities=entities)
    s.graph = MemoryGraph(s.store, entities)
    with client:
        yield client, s


def save(client, s, text, objects, day):
    body = {**DREAM, "originalText": text, "objects": [{"label": o, "meaning": ""} for o in objects]}
    d = client.post("/api/v1/dreams", headers=auth(), json=body).json()
    d = client.patch(f"/api/v1/dreams/{d['id']}/journal", headers=auth(),
                     json={"revision": d["revision"], "dreamedOn": f"2026-10-{day:02d}"}).json()
    deadline = time.time() + 10
    while time.time() < deadline:
        jobs = [j for j in s.queue.jobs.values() if j.kind == "index" and j.dream_id == d["id"]]
        if jobs and all(j.status == "done" for j in jobs):
            return d
        time.sleep(0.02)
    raise AssertionError("index did not finish")


def test_saving_dreams_writes_and_replaces_their_links(brain_api):
    client, s = brain_api
    a = save(client, s, "Denizde annemle yüzdüm, çok korktum.", ["deniz", "anne"], 1)
    b = save(client, s, "Yine deniz ve annem vardı, korktum.", ["deniz", "anne"], 12)
    c = save(client, s, "Bir kütüphanede kitap okudum.", ["kitap"], 25)
    pair = tuple(sorted((a["id"], b["id"])))
    rows = {(r["relation"], r["source_id"], r["target_id"]) for r in s.graph.rows}
    assert ("shares_content", *pair) in rows and ("shares_emotion", *pair) in rows
    assert not any(c["id"] in (r["source_id"], r["target_id"]) for r in s.graph.rows)  # unrelated: no links

    client.patch(f"/api/v1/dreams/{b['id']}/journal", headers=auth(),
                 json={"revision": b["revision"], "originalText": "Bir kütüphanede kitap okudum, mutluydum."})
    deadline = time.time() + 10
    while time.time() < deadline and any(r["relation"] == "shares_emotion" and b["id"] in (r["source_id"], r["target_id"]) for r in s.graph.rows):
        time.sleep(0.02)
    assert not any(r["relation"] == "shares_emotion" and b["id"] in (r["source_id"], r["target_id"]) for r in s.graph.rows)


def test_the_brain_answer_holds_every_dream_and_its_links(brain_api):
    client, s = brain_api
    a = save(client, s, "Denizde annemle yüzdüm, çok korktum.", ["deniz", "anne"], 1)
    b = save(client, s, "Yine deniz ve annem vardı, korktum.", ["deniz", "anne"], 12)
    c = save(client, s, "Bir kütüphanede kitap okudum.", ["kitap"], 25)
    res = client.get("/api/v1/brain", headers=auth())
    assert res.status_code == 200
    brain = res.json()
    spec = client.app.openapi()
    check(spec, spec["paths"]["/api/v1/brain"]["get"]["responses"]["200"]["content"]["application/json"]["schema"], brain)
    assert brain["relations"] == ["shares_content", "shares_concept", "shares_emotion", "near_in_time", "series"]
    nodes = {d["id"]: d for d in brain["dreams"]}
    assert [d["id"] for d in brain["dreams"]] == [a["id"], b["id"], c["id"]]  # by the day dreamt
    assert nodes[a["id"]]["dated"] == "2026-10-01" and nodes[a["id"]]["emotions"] == ["apprehension"]
    assert nodes[c["id"]]["degree"] == 0 and nodes[a["id"]]["degree"] >= 2  # c floats free
    content = next(l for l in brain["links"] if l["relation"] == "shares_content")
    assert {content["source"], content["target"]} == {a["id"], b["id"]}
    assert {x["key"] for x in content["evidence"]["shared"]} >= {"sym.deniz"}
    assert client.get("/api/v1/brain", headers=auth("dev-someone-else-entirely")).json()["dreams"] == []


def test_the_brain_needs_accounts(api):
    client, _ = api
    assert client.get("/api/v1/brain").status_code == 401
    assert client.get("/api/v1/brain", headers=auth()).json()["code"] == "service_off"


def test_the_dreamer_links_and_hides_by_hand(brain_api):
    client, s = brain_api
    a = save(client, s, "Denizde annemle yüzdüm, çok korktum.", ["deniz", "anne"], 1)
    b = save(client, s, "Yine deniz ve annem vardı, korktum.", ["deniz", "anne"], 12)
    c = save(client, s, "Bir kütüphanede kitap okudum.", ["kitap"], 25)
    edit = lambda x, y, action, on=True: client.post("/api/v1/brain/links", headers=auth(),
                                                     json={"a": x["id"], "b": y["id"], "action": action, "on": on})
    linked = edit(c, a, "link").json()
    mine = [l for l in linked["links"] if l["relation"] == "series"]
    assert len(mine) == 1 and {mine[0]["source"], mine[0]["target"]} == {a["id"], c["id"]}
    assert next(d for d in linked["dreams"] if d["id"] == c["id"])["degree"] == 1  # no longer floating

    hidden = edit(b, a, "hide").json()
    pair = {a["id"], b["id"]}
    assert not any({l["source"], l["target"]} == pair for l in hidden["links"])  # every scored link of the pair hidden
    shown = edit(a, b, "hide", on=False).json()
    assert any({l["source"], l["target"]} == pair for l in shown["links"])

    save(client, s, "Yine deniz ve annem vardı, korktum.", ["deniz", "anne"], 2)  # re-scoring keeps the hand-made link
    assert any(l["relation"] == "series" for l in client.get("/api/v1/brain", headers=auth()).json()["links"])
    assert edit(a, a, "link").json()["code"] == "invalid_request"
    other = client.post("/api/v1/dreams", headers=auth("dev-someone-else-entirely"), json=DREAM).json()
    assert edit(a, other, "link").status_code == 404
