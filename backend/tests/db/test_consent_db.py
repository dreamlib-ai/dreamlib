"""R1 against the real database: set_dream_tier keeps the ledger, closes a public magazine and feeds the access rule."""
from app.store.magazines import SupabaseMagazines

from .conftest import run, sql
from .test_dream_store import dream


def active(dream_id):
    return sql(f"select scope || ':' || text_version from consents where dream_id = '{dream_id}' and withdrawn_at is null "
               "order by scope").splitlines()


def test_tiers_write_and_withdraw_consents_in_one_step(sb, user, other):
    saved = run(sb.save_dream(user, dream()))
    assert run(sb.set_tier(other, saved.id, "public", "consent@1")) is None  # not theirs
    assert run(sb.set_tier(user, saved.id, "public", "consent@1")) == "public"
    assert active(saved.id) == ["collective:consent@1", "public:consent@1"]
    mags = SupabaseMagazines(sb)
    run(mags.put(user, saved.id, {"version": 1}, "", 0))
    sql(f"update magazines set visibility = 'public' where dream_id = '{saved.id}'")
    assert run(sb.set_tier(user, saved.id, "collective", "consent@2")) == "collective"
    assert active(saved.id) == ["collective:consent@2"]  # the new wording replaces the old consent
    assert run(mags.for_dream(user, saved.id))["visibility"] == "private"  # no longer public: its magazine closes
    assert run(sb.get_dream(user, saved.id)).visibility == "collective"
    assert run(sb.set_tier(user, saved.id, "private", "")) == "private"
    assert active(saved.id) == [] and sql(f"select count(*) from consents where dream_id = '{saved.id}'") == "3"


def test_other_peoples_dreams_join_a_search_only_when_asked_and_consented(user, other):
    mine = sql(f"insert into dreams (user_id, title, original_text) values ('{user}', 'a', 'a') returning id")
    theirs = sql(f"insert into dreams (user_id, title, original_text) values ('{other}', 'b', 'b') returning id")
    koala = sql("insert into public.entities (kind, key) values ('symbol', 'koala-r1') returning id")
    try:
        for d in (mine, theirs):
            sql(f"insert into public.dream_entities (dream_id, entity_id, source) values ('{d}', '{koala}', 'model')")
        assert sql(f"select count(*) from public.dream_chain('{user}', '{mine}', 2, true)") == "0"  # theirs is private
        sql(f"select public.set_dream_tier('{other}', '{theirs}', 'collective', 'consent@1')")
        assert sql(f"select count(*) from public.dream_chain('{user}', '{mine}', 2)") == "0"  # own dreams by default
        assert sql(f"select dream_id from public.dream_chain('{user}', '{mine}', 2, true)") == theirs
    finally:
        sql("delete from public.entities where key = 'koala-r1'")
