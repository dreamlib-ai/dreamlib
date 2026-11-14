"""M6: loads corpus/lexicon/lexicon-a.jsonl into a database as approved symbol nodes, aliases and lexicon rows.

Idempotent: a symbol node is found by (symbol, key) or opened; a candidate the index job opened earlier with the
same key (sym.<Turkish slug>) becomes approved, so dreams that named it are already linked. Rows are updated in
place by (source, locator, symbol). One transaction.

    python scripts/seed_lexicon.py --local        # the dreamlib-local stack (npm run db -- up)
    python scripts/seed_lexicon.py --sql out.sql  # the SQL alone, to run elsewhere (the live database)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "corpus" / "lexicon" / "lexicon-a.jsonl"
TAG = "$lexicon$"


def sql(rows: list[str] | None = None) -> str:
    """The seed as one transaction; `rows` (JSON lines) default to the lexicon file."""
    rows = rows if rows is not None else [line.strip() for line in LEXICON.open(encoding="utf-8") if line.strip()]
    if any(TAG in r for r in rows):
        raise SystemExit("a row holds the quoting tag; change TAG")
    values = ",\n".join(f"({TAG}{r}{TAG}::jsonb)" for r in rows)
    return f"""begin;
create temp table lx (j jsonb) on commit drop;
insert into lx (j) values
{values};

insert into public.entities (kind, key, labels, qid, status)
select distinct on (j->>'key') 'symbol', j->>'key', j->'labels', j->>'qid', 'approved' from lx order by j->>'key'
on conflict (kind, key) do update
   set status = 'approved', qid = excluded.qid, labels = public.entities.labels || excluded.labels, updated_at = now()
 where public.entities.status <> 'merged';

insert into public.entity_aliases (alias, lang, entity_id)
select distinct lower(a), 'tr', e.id
  from lx cross join lateral (select j->'labels'->>'tr' union select jsonb_array_elements_text(j->'aliases_tr')) as names(a)
  join public.entities e on e.kind = 'symbol' and e.key = lx.j->>'key'
 where coalesce(a, '') <> ''
on conflict do nothing;

insert into public.lexicon_entries (entity_id, tradition, language, heading, meaning, source, locator, url, license,
                                    rights_holder, attributed_author)
select e.id, j->>'tradition', j->>'language', j->>'heading', j->>'meaning', j->>'source', j->>'locator', j->>'url',
       j->>'license', j->>'rights_holder', j->>'attributed_author'
  from lx join public.entities e on e.kind = 'symbol' and e.key = lx.j->>'key'
on conflict (source, locator, entity_id) do update
   set heading = excluded.heading, meaning = excluded.meaning, url = excluded.url, license = excluded.license;
commit;
"""


def main() -> int:
    if sys.argv[1:2] == ["--sql"] and len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(sql(), encoding="utf-8")
        return 0
    if sys.argv[1:] == ["--local"]:
        sys.path.insert(0, str(ROOT / "scripts"))
        import local_db
        out = Path(local_db.ROOT / "corpus" / "lexicon" / ".seed.sql")
        out.write_text(sql(), encoding="utf-8")
        try:
            print(local_db.LOCAL.must(local_db.LOCAL.psql(file=out), "lexicon seed") or "seeded")
        finally:
            out.unlink()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
