"""M7 against the real database: the collective total of a symbol shows only from five people's consented dreams."""
import uuid

from .conftest import run, sql


def people(n: int) -> list[str]:
    ids = [str(uuid.uuid4()) for _ in range(n)]
    for uid in ids:
        sql(f"insert into auth.users (id, email) values ('{uid}', '{uid}@test.local')")
    return ids


def dream_with(user: str, tier: str, *entities: str) -> str:
    did = sql(f"insert into dreams (user_id, title, original_text, visibility) values ('{user}', 't', 't', '{tier}') returning id")
    for e in entities:
        sql(f"insert into public.dream_entities (dream_id, entity_id, source) values ('{did}', '{e}', 'model')")
    return did


def totals(symbol: str) -> str:
    return sql(f"select coalesce(string_agg(emotion || ':' || dreams || ':' || people, ','), '') "
               f"from public.symbol_emotions(array['{symbol}']::uuid[])")


def test_the_total_needs_five_people_and_their_consent(sb):
    users = people(6)
    snake = sql("insert into public.entities (kind, key) values ('symbol', 'sym.m7-yilan') returning id")
    fear = sql("insert into public.entities (kind, key) values ('emotion', 'hvdc.m7-apprehension') returning id")
    free = sql("insert into public.entities (kind, key) values ('emotion', 'm7-serbest') returning id")
    try:
        for u in users[:4]:
            dream_with(u, "collective", snake, fear, free)
        dream_with(users[4], "private", snake, fear)
        assert totals(snake) == ""  # four consenting people, one private: not enough
        assert sql(f"select count(*) from public.symbol_emotions(array['{snake}']::uuid[], 1)") == "0"  # the floor stays five
        dream_with(users[5], "public", snake, fear)
        assert totals(snake) == "hvdc.m7-apprehension:5:5"  # free labels are not counted, only HVdC classes
        assert run(sb._do("POST", "/rest/v1/rpc/symbol_emotions", sb.key, json_body={"p_entities": [snake]})).json()[0]["people"] == 5
        assert sql("select has_function_privilege('anon', 'public.symbol_emotions(uuid[], int)', 'execute') or "
                   "has_function_privilege('authenticated', 'public.symbol_emotions(uuid[], int)', 'execute')") == "f"
    finally:
        sql("delete from public.entities where key in ('sym.m7-yilan', 'hvdc.m7-apprehension', 'm7-serbest')")
        for u in users:
            sql(f"delete from auth.users where id = '{u}'")
