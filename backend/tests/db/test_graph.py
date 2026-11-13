"""M2: edges, dream vectors and the two search functions on real Postgres + pgvector."""
import uuid

import pytest

from .conftest import SqlError, run, sql


def new_dream(user: str) -> str:
    did = str(uuid.uuid4())
    sql(f"insert into public.dreams (id, user_id, title, original_text) values ('{did}', '{user}', 't', 't')")
    return did


def embed(dream: str, vec: list[float], model: str = "test-3") -> None:
    sql(f"insert into public.dream_embeddings (dream_id, kind, model, dims, embedding) "
        f"values ('{dream}', 'narrative', '{model}', {len(vec)}, '{vec}')")


@pytest.fixture
def other():
    uid = str(uuid.uuid4())
    sql(f"insert into auth.users (id, email) values ('{uid}', '{uid}@test.local')")
    yield uid
    sql(f"delete from auth.users where id = '{uid}'")


def test_neighbors_are_nearest_first_and_only_the_owners(sb, user, other):
    a, near, far, mine_other_model = (new_dream(user) for _ in range(4))
    stranger = new_dream(other)
    embed(a, [1, 0, 0])
    embed(near, [0.9, 0.1, 0])
    embed(far, [0, 0, 1])
    embed(mine_other_model, [1, 0, 0], model="other-3")
    embed(stranger, [1, 0, 0])  # identical, but not theirs

    async def rpc():
        res = await sb._do("POST", "/rest/v1/rpc/dream_neighbors", sb.key,
                           json_body={"p_user": user, "p_dream": a, "p_kind": "narrative", "p_model": "test-3", "p_limit": 5})
        assert res.status_code == 200, res.text
        return res.json()

    rows = run(rpc())
    assert [r["dream_id"] for r in rows] == [near, far]
    assert rows[0]["distance"] < rows[1]["distance"]


def test_asking_about_someone_elses_dream_returns_nothing(user, other):
    a, b = new_dream(user), new_dream(user)
    embed(a, [1, 0, 0])
    embed(b, [0.9, 0.1, 0])
    assert sql(f"select count(*) from public.dream_neighbors('{other}', '{a}', 'narrative', 'test-3', 5)") == "0"


def test_vectors_must_match_their_stated_size(user):
    d = new_dream(user)
    with pytest.raises(SqlError):
        sql(f"insert into public.dream_embeddings (dream_id, kind, model, dims, embedding) values ('{d}', 'narrative', 'm', 4, '[1,2,3]')")


def test_chain_walks_shared_nodes_up_to_the_depth_and_never_leaves_the_owner(user, other):
    a, b, c, d = (new_dream(user) for _ in range(4))
    stranger = new_dream(other)
    koala = sql("insert into public.entities (kind, key) values ('symbol', 'koala-g') returning id")
    sea = sql("insert into public.entities (kind, key) values ('symbol', 'sea-g') returning id")
    moon = sql("insert into public.entities (kind, key) values ('symbol', 'moon-g') returning id")
    for dream, ent in [(a, koala), (b, koala), (b, sea), (c, sea), (c, moon), (d, moon), (stranger, koala)]:
        sql(f"insert into public.dream_entities (dream_id, entity_id, source) values ('{dream}', '{ent}', 'model')")
    try:
        two = sql(f"select dream_id, depth from public.dream_chain('{user}', '{a}', 2) order by depth, dream_id")
        assert two.splitlines() == [f"{b}|1", f"{c}|2"]
        three = sql(f"select count(*) from public.dream_chain('{user}', '{a}', 9)")  # capped at three
        assert three == "3"
        assert sql(f"select count(*) from public.dream_chain('{other}', '{a}', 3)") == "0"  # not their dream
    finally:
        sql("delete from public.entities where key in ('koala-g', 'sea-g', 'moon-g')")


def test_symmetric_edges_are_written_once_in_order(user):
    a, b = sorted([new_dream(user), new_dream(user)])
    sql(f"insert into public.edges (relation, source_id, target_id, user_id, weight, evidence) "
        f"values ('similar', '{a}', '{b}', '{user}', 0.8, '{{\"shared\": [\"koala\"]}}')")
    with pytest.raises(SqlError):  # the reverse copy
        sql(f"insert into public.edges (relation, source_id, target_id, user_id, weight) values ('similar', '{b}', '{a}', '{user}', 0.8)")
    with pytest.raises(SqlError):  # weight out of range
        sql(f"insert into public.edges (relation, source_id, target_id, user_id, weight) values ('series', '{a}', '{b}', '{user}', 1.5)")
    sql(f"insert into public.edges (relation, source_id, target_id, user_id, weight) values ('series', '{b}', '{a}', '{user}', 1)")  # directed: fine


def test_deleting_a_dream_takes_its_edges_and_vectors(user):
    a, b = sorted([new_dream(user), new_dream(user)])
    embed(a, [1, 0])
    sql(f"insert into public.edges (relation, source_id, target_id, user_id, weight) values ('similar', '{a}', '{b}', '{user}', 0.5)")
    sql(f"delete from public.dreams where id = '{b}'")
    assert sql(f"select count(*) from public.edges where source_id = '{a}' or target_id = '{a}'") == "0"
    sql(f"delete from public.dreams where id = '{a}'")
    assert sql(f"select count(*) from public.dream_embeddings where dream_id = '{a}'") == "0"


def test_clients_cannot_call_the_search_functions(user):
    with pytest.raises(SqlError):
        sql(f"set role authenticated; select * from public.dream_chain('{user}', '{user}', 2);")
    with pytest.raises(SqlError):
        sql(f"set role anon; select * from public.dream_neighbors('{user}', '{user}', 'narrative', 'm', 5);")
