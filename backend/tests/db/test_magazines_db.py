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


def test_a_shared_magazine_is_found_by_its_slug_only_while_shared(sb, user):
    mags = SupabaseMagazines(sb)
    saved = run(sb.save_dream(user, dream()))
    run(mags.put(user, saved.id, {"version": 1}, "u/1.png", 0))
    assert run(mags.share("00000000-0000-4000-8000-0000000000bb", saved.id, "link")) is None  # not theirs
    row = run(mags.share(user, saved.id, "link"))
    slug = row["share_slug"]
    assert row["visibility"] == "link" and len(slug) == 12 and run(mags.by_slug(slug))["id"] == row["id"]
    run(mags.share(user, saved.id, "private"))
    assert run(mags.by_slug(slug)) is None and run(mags.share(user, saved.id, "link"))["share_slug"] == slug
    sql(f"update magazines set status = 'withdrawn' where id = '{row['id']}'")
    assert run(mags.by_slug(slug)) is None and run(mags.by_slug("../x")) is None


def test_the_dreams_of_one_night_by_journal_date_or_by_when_they_were_saved(sb, user):
    from datetime import datetime, timedelta, timezone
    dated = run(sb.save_dream(user, dream()))
    sql(f"update dreams set journal = jsonb_set(journal, '{{dreamedOn}}', '\"2025-11-15\"') where id = '{dated.id}'")
    saved = run(sb.save_dream(user, dream()))
    sql(f"update dreams set created_at = '2025-11-14T22:30:00+00:00' where id = '{saved.id}'")  # 01:30 the 15th in Istanbul
    start = datetime(2025, 11, 15, tzinfo=timezone.utc) - timedelta(minutes=180)
    assert run(sb.dream_ids_on(user, "2025-11-15", start, start + timedelta(days=1))) == [dated.id, saved.id]
    utc = datetime(2025, 11, 15, tzinfo=timezone.utc)
    assert run(sb.dream_ids_on(user, "2025-11-15", utc, utc + timedelta(days=1))) == [dated.id]
