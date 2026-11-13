import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def files():
    return sorted(MIGRATIONS.glob("*.sql"))


def test_versions_are_unique_and_well_formed():
    versions = [p.name.split("_", 1)[0] for p in files()]
    assert all(re.fullmatch(r"\d{14}", v) for v in versions), versions
    assert len(versions) == len(set(versions))


def test_every_public_table_has_row_level_security():
    sql = "\n".join(p.read_text(encoding="utf-8").lower() for p in files())
    tables = set(re.findall(r"create table public\.(\w+)", sql))
    secured = set(re.findall(r"alter table public\.(\w+) enable row level security", sql))
    assert tables and tables <= secured, sorted(tables - secured)
