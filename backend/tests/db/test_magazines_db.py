"""G4 against the real table: one magazine per dream, rewritten in place, gone with the dream."""
from app.store.magazines import SupabaseMagazines

from .conftest import SqlError, run, sql
from .test_dream_store import dream


def test_one_magazine_per_dream_kept_private_and_removed_with_it(sb, user):
    mags = SupabaseMagazines(sb)
    saved = run(sb.save_dream(user, dream()))
    first = run(mags.put(user, saved.id, {"version": 1, "pages": []}, "u/1.png", 0))
    sql(f"update magazines set visibility = 'link', share_slug = 'abc' where id = '{first}'")
    again = run(mags.put(user, saved.id, {"version": 1, "pages": [{"layout": "full"}]}, "u/2.png", 1))
    row = run(mags.for_dream(user, saved.id))
    assert again == first and row["cover_path"] == "u/2.png" and row["dream_revision"] == 1
    assert row["visibility"] == "link" and row["share_slug"] == "abc"  # a new layout keeps how it is shared
    assert run(mags.for_dream("00000000-0000-4000-8000-0000000000bb", saved.id)) is None
    assert run(mags.for_dream(user, "not-a-uuid")) is None
    try:
        sql(f"update magazines set visibility = 'friends' where id = '{first}'")
    except SqlError:
        pass
    else:
        raise AssertionError("an unknown visibility got in")
    run(sb.delete_dream(user, saved.id))
    assert sql(f"select count(*) from magazines where id = '{first}'") == "0"
    saved = run(sb.save_dream(user, dream()))
    run(mags.put(user, saved.id, {}, "", 0))
    run(mags.remove(user, saved.id))
    assert run(mags.for_dream(user, saved.id)) is None
