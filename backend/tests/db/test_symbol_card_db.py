"""F1 against the real database: a symbol card counts only the reader's own dreams and shows only approved symbols."""
from .conftest import run, sql


def test_seen_counts_the_readers_dreams_and_symbol_needs_an_approved_node(sb, user, other):
    from app.store.lexicon import SupabaseLexicon
    lex = SupabaseLexicon(sb)
    snake = sql("insert into public.entities (kind, key, labels, status) values ('symbol', 'sym.f1-yilan', '{\"tr\":\"yılan\"}', 'approved') returning id")
    cand = sql("insert into public.entities (kind, key, status) values ('symbol', 'sym.f1-aday', 'candidate') returning id")
    try:
        for owner in (user, user, other):
            d = sql(f"insert into dreams (user_id, title, original_text) values ('{owner}', 't', 't') returning id")
            sql(f"insert into public.dream_entities (dream_id, entity_id, source) values ('{d}', '{snake}', 'model')")
        assert run(lex.seen(user, snake)) == 2 and run(lex.seen(other, snake)) == 1
        node = run(lex.symbol(snake))
        assert node["labels"]["tr"] == "yılan" and run(lex.symbol(cand)) is None
    finally:
        sql("delete from public.entities where key in ('sym.f1-yilan', 'sym.f1-aday')")
