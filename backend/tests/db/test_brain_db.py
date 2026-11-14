"""BG1 against the real tables: brain_links, scored edges replaced per dream, and edges gone with the dream."""
import uuid
from datetime import date

from app.engine.relations import relate
from app.store.entities import Link, Node, SupabaseEntities
from app.store.graph import SupabaseGraph

from .conftest import run, sql


def test_the_corpus_scores_into_edges_that_follow_the_dreams(sb, user, dream):
    other, lonely = str(uuid.uuid4()), str(uuid.uuid4())
    sql(f"insert into public.dreams (id, user_id, title, original_text, journal) values "
        f"('{other}', '{user}', 'b', 'b', '{{\"dreamedOn\": \"2026-10-02\"}}'), ('{lonely}', '{user}', 'c', 'c', '{{}}')")
    sql(f"update public.dreams set journal = '{{\"dreamedOn\": \"2026-10-01\"}}' where id = '{dream}'")
    e = SupabaseEntities(sb)
    sea = Node("symbol", f"test.sea{uuid.uuid4().hex[:6]}", {"tr": "deniz"})
    try:
        sid = run(e.ensure([sea], "candidate"))[sea.key]
        for d in (dream, other):
            run(e.link(d, "interpret.objects@1", [Link(sid, 1.0, "deniz")]))
        g = SupabaseGraph(sb)
        corpus = {d.id: d for d in run(g.corpus(user))}
        assert set(corpus) == {dream, other, lonely} and corpus[other].dated == date(2026, 10, 2)
        assert corpus[lonely].nodes == {} and corpus[dream].nodes[sid].label == "deniz"

        edges = relate(dream, list(corpus.values()))
        assert {e.relation for e in edges} == {"shares_content", "near_in_time"}
        run(g.replace(user, dream, edges))  # the symmetric-order trigger accepts sorted ids
        run(g.replace(user, dream, edges))  # replacing does not pile up
        rows = run(g.edges(user))
        assert sorted(r["relation"] for r in rows) == ["near_in_time", "shares_content"]
        assert rows[0]["evidence"] and all(lonely not in (r["source_id"], r["target_id"]) for r in rows)

        sql(f"delete from public.dreams where id = '{other}'")
        assert run(g.edges(user)) == []  # edges leave with either dream
    finally:
        sql(f"delete from entities where key = '{sea.key}'")


def test_the_dreamers_own_marks_survive_rescoring(sb, user, dream):
    other = str(uuid.uuid4())
    sql(f"insert into public.dreams (id, user_id, title, original_text) values ('{other}', '{user}', 'b', 'b')")
    g = SupabaseGraph(sb)
    run(g.mark(user, other, dream, "series", True))   # either order; stored sorted
    run(g.mark(user, dream, other, "hidden", True))
    run(g.replace(user, dream, []))                    # scoring clears only its own relations
    assert sorted(r["relation"] for r in run(g.edges(user))) == ["hidden", "series"]
    run(g.mark(user, dream, other, "hidden", False))
    assert [r["relation"] for r in run(g.edges(user))] == ["series"]
