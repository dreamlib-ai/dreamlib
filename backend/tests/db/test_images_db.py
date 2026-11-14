"""G3 against the real table: layout facts read back by path; bad colours refused."""
from .conftest import SqlError, run, sql


def test_layout_facts_are_read_back_by_path(sb, user):
    path = f"{user}/a.png"
    sql(f"insert into images (path, user_id, width, height, blurhash, color, thumb_path) values "
        f"('{path}', '{user}', 1024, 768, 'LKO2', '#102343', '{path}.t.webp')")
    got = run(sb.image_meta([path, f"{user}/missing.png"]))
    assert list(got) == [path] and got[path]["width"] == 1024 and got[path]["thumb_path"] == f"{path}.t.webp"
    assert run(sb.image_meta([])) == {}
    try:
        sql(f"insert into images (path, user_id, width, height, color) values ('{user}/b.png', '{user}', 1, 1, 'red')")
    except SqlError:
        pass
    else:
        raise AssertionError("a colour that is not #rrggbb got in")
    sql(f"delete from auth.users where id = '{user}'")
    assert sql(f"select count(*) from images where user_id = '{user}'") == "0"  # leaves with the account
