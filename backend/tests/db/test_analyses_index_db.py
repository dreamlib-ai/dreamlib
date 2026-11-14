"""M3 analyses rows, M4 node links and the background-job lock rule against the real tables."""
import uuid

from app.store.analyses import SupabaseAnalyses
from app.store.entities import Link, Node, SupabaseEntities

from .conftest import run, sql


def test_an_interpretation_row_is_attached_once_and_only_by_its_owner(sb, user, dream):
    a = SupabaseAnalyses(sb)
    aid = run(a.add(user, "interpret", {"interpretation": "x"}, prompt="interpret@1", model="m/one", input_text="metin"))
    other = str(uuid.uuid4())
    sql(f"insert into auth.users (id, email) values ('{other}', '{other}@test.local')")
    try:
        assert not run(a.attach(other, aid, dream))  # someone else's row
        assert run(a.attach(user, aid, dream))
        assert not run(a.attach(user, aid, dream))  # already attached
    finally:
        sql(f"delete from auth.users where id = '{other}'")
    rows = run(a.for_dream(user, dream))
    assert [(r["pipeline"], r["prompt"], r["model"]) for r in rows] == [("interpret", "interpret@1", "m/one")]
    assert len(rows[0]["input_sha256"]) == 64 and rows[0]["output"] == {"interpretation": "x"}


def test_bad_pipeline_names_are_refused(sb, user):
    a = SupabaseAnalyses(sb)
    try:
        run(a.add(user, "Not A Pipeline", {}))
    except RuntimeError as e:
        assert "status 400" in str(e)
    else:
        raise AssertionError("the pipeline check let a bad name in")


def test_nodes_open_once_and_links_are_replaced_per_extractor(sb, user, dream):
    e = SupabaseEntities(sb)
    fear = Node("emotion", f"test.fear{uuid.uuid4().hex[:6]}", {"tr": "Korku", "en": "Fear"})
    joy = Node("emotion", f"test.joy{uuid.uuid4().hex[:6]}", {"tr": "Mutluluk", "en": "Joy"})
    try:
        ids = run(e.ensure([fear, joy]))
        assert run(SupabaseEntities(sb).ensure([fear])) == {fear.key: ids[fear.key]}  # a fresh client finds, not duplicates
        run(e.link(dream, "lab.emotions@1", [Link(ids[fear.key], 1.0, "korktum")]))
        run(e.link(dream, "lab.emotions@1", [Link(ids[joy.key], 1.0, "sevindim")]))
        got = sql(f"select entity_id || '|' || quote || '|' || extractor from dream_entities where dream_id = '{dream}'")
        assert got == f"{ids[joy.key]}|sevindim|lab.emotions@1"
        run(e.link(dream, "lab.emotions@1", []))
        assert sql(f"select count(*) from dream_entities where dream_id = '{dream}'") == "0"
    finally:
        sql(f"delete from entities where key in ('{fear.key}', '{joy.key}')")


def test_background_jobs_do_not_take_the_user_lock(user):
    sql(f"insert into jobs (user_id, kind, input, exclusive) values ('{user}', 'index', '{{}}', false)")
    assert sql(f"select lock_user('{user}', 'tok', 30, true)") == "t"  # an index job alone does not lock
    sql(f"delete from user_locks where user_id = '{user}'")
    sql(f"insert into jobs (user_id, kind, input, exclusive) values ('{user}', 'manga', '{{}}', true)")
    assert sql(f"select lock_user('{user}', 'tok', 30, true)") == "f"  # a drawing job still does
