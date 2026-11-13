import pytest

from .conftest import SqlError, sql

TABLES = {"profiles", "dreams", "jobs", "call_log", "user_locks", "usage", "generation_timings", "relation_types", "edges", "dream_embeddings",
          "entity_kinds", "entities", "entity_aliases", "dream_entities"}


def test_every_table_exists_with_row_level_security():
    rows = sql("select relname, relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace "
               "where n.nspname = 'public' and c.relkind = 'r'")
    found = dict(line.split("|") for line in rows.splitlines())
    assert TABLES <= set(found), TABLES - set(found)
    assert all(v == "t" for v in found.values()), {k for k, v in found.items() if v != "t"}


def test_clients_cannot_read_private_tables():
    """No policies: anon and authenticated roles see nothing; only the service key reads."""
    for role in ("anon", "authenticated"):
        out = sql(f"set role {role}; select count(*) from public.jobs;")
        assert out.splitlines()[-1] == "0"


def test_queue_functions_are_not_callable_by_clients():
    with pytest.raises(SqlError):
        sql("set role authenticated; select * from public.claim_job('w', 60, 3);")


def test_pgvector_is_installed_and_entity_kinds_are_seeded():
    assert sql("select extname from pg_extension where extname = 'vector'") == "vector"
    assert int(sql("select count(*) from public.entity_kinds")) == 11


def test_entity_rules_hold(user):
    a = sql("insert into public.entities (kind, key) values ('symbol', 'koala') returning id")
    with pytest.raises(SqlError):  # merged without a target
        sql(f"update public.entities set status = 'merged' where id = '{a}'")
    with pytest.raises(SqlError):  # unknown kind
        sql("insert into public.entities (kind, key) values ('nope', 'x')")
    with pytest.raises(SqlError):  # duplicate kind + key
        sql("insert into public.entities (kind, key) values ('symbol', 'koala')")
    sql("insert into public.entities (kind, key, embedding, embed_model) values ('theme', 'chased', '[0.1,0.2,0.3]', 'test')")
    sql("delete from public.entities where key in ('koala', 'chased')")
