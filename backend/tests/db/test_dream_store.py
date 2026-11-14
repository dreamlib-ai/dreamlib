"""The dream store (app.store.supabase) against the real dreams table."""
import pytest

from app.errors import Conflict, NotFound
from app.models import Dream, MangaMeta, Panel

from .conftest import run, sql


def dream(**kw) -> Dream:
    return Dream(title="Uçan orman", originalText="Ormanın üstünde uçuyordum.", cleanText="Ormanın üstünde uçuyordum.",
                 type="universal", interpretation="Özgürlük arzusu.", mood="huzurlu", tags=["uçmak"],
                 panels=[Panel(caption="bir", path="u/1.png"), Panel(caption="iki", path="u/2.png")], style="manga",
                 visibility="private", **kw)  # the route fills this in before saving


def test_save_read_list_and_delete_keep_every_field(sb, user):
    meta = MangaMeta(style="manga", scenes=["a", "b"], consistent=True, prompt_version="image@1", image_model="fast")
    saved = run(sb.save_dream(user, dream(manga_meta=meta)))
    got = run(sb.get_dream(user, saved.id))
    assert (got.title, got.tags, [p.path for p in got.panels]) == ("Uçan orman", ["uçmak"], ["u/1.png", "u/2.png"])
    assert got.manga_meta.prompt_version == "image@1" and got.manga_meta.image_model == "fast"
    assert [d.id for d in run(sb.list_dreams(user))] == [saved.id]
    run(sb.delete_dream(user, saved.id))
    with pytest.raises(NotFound):
        run(sb.get_dream(user, saved.id))


def test_list_pages_by_created_at_then_id(sb, user):
    saved = [run(sb.save_dream(user, dream())) for _ in range(3)]
    tie = saved[0].createdAt
    sql(f"update public.dreams set created_at = '{tie.isoformat()}' where user_id = '{user}'")  # one instant, id decides
    whole = run(sb.list_dreams(user))
    assert len(whole) == 3 and [d.id for d in whole] == sorted((d.id for d in saved), reverse=True)
    seen, before = [], None
    while page := run(sb.list_dreams(user, limit=1, before=before)):
        seen.append(page[0].id)
        before = (page[0].createdAt, page[0].id)
    assert seen == [d.id for d in whole]


def test_another_account_can_neither_read_nor_overwrite(sb, user):
    other = "00000000-0000-4000-8000-0000000000aa"
    sql(f"insert into auth.users (id, email) values ('{other}', 'other@test.local') on conflict do nothing")
    try:
        saved = run(sb.save_dream(user, dream()))
        with pytest.raises(NotFound):
            run(sb.get_dream(other, saved.id))
        with pytest.raises(NotFound):  # same id from another owner must not merge into theirs
            run(sb.save_dream(other, dream(id=saved.id)))
        assert run(sb.get_dream(user, saved.id)).title == "Uçan orman"
    finally:
        sql(f"delete from auth.users where id = '{other}'")


def test_panel_swap_and_journal_edit_refuse_stale_writes(sb, user):
    saved = run(sb.save_dream(user, dream()))
    after = [Panel(caption="bir", path="u/1b.png"), saved.panels[1]]
    run(sb.replace_panels(user, saved.id, saved.panels, after, MangaMeta(style="manga")))
    with pytest.raises(Conflict):  # based on panels that are no longer there
        run(sb.replace_panels(user, saved.id, saved.panels, after, MangaMeta(style="manga")))

    current = run(sb.get_dream(user, saved.id))
    current.title = "Yeni başlık"
    run(sb.update_journal(user, current, current.revision))
    with pytest.raises(Conflict):  # the same revision twice
        run(sb.update_journal(user, current, current.revision))
    assert run(sb.get_dream(user, saved.id)).title == "Yeni başlık"
