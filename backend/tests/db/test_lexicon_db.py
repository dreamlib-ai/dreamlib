"""M6 against the real database: the seed approves symbol nodes, adds aliases and lexicon rows, and can run again."""
import json
import os
import subprocess
import sys
from pathlib import Path

from .conftest import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import seed_lexicon  # noqa: E402


def run_sql(text: str) -> None:
    res = subprocess.run(
        ["docker", "compose", "-p", os.environ["DREAMLIB_DB_PROJECT"], "-f", os.environ["DREAMLIB_DB_COMPOSE"],
         "exec", "-T", "db", "psql", "-U", "postgres", "-d", os.environ["DREAMLIB_DB_PROJECT"], "-qAt", "-v", "ON_ERROR_STOP=1"],
        input=text, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, res.stderr


def row(key: str, heading: str, locator: str, meaning: str = "If any one dreams of a serpent...") -> str:
    return json.dumps({"key": key, "qid": "Q2102", "labels": {"tr": "yılan", "en": "snake"}, "aliases_tr": ["Yılanlar"],
                       "tradition": "greko-romen", "language": "en", "heading": heading, "meaning": meaning,
                       "source": "lx-test", "locator": locator, "url": "https://example.test", "license": "CC0 1.0",
                       "rights_holder": "", "attributed_author": "Artemidorus"}, ensure_ascii=False)


def test_the_seed_approves_symbols_links_meanings_and_runs_again():
    sql("insert into public.entities (kind, key, labels, status) values ('symbol', 'sym.lx-yilan', '{\"tr\":\"yılan\"}', 'candidate')")
    try:
        rows = [row("sym.lx-yilan", "Of Serpents.", "II.13"), row("sym.lx-yilan", "Of Dragons.", "II.14")]
        run_sql(seed_lexicon.sql(rows))
        node = sql("select status || '|' || qid || '|' || (labels->>'en') from public.entities where key = 'sym.lx-yilan'")
        assert node == "approved|Q2102|snake"  # the dreams' own candidate became the lexicon's symbol
        assert sql("select string_agg(alias, ',' order by alias) from public.entity_aliases a join public.entities e "
                   "on e.id = a.entity_id where e.key = 'sym.lx-yilan'") == "yılan,yılanlar"
        run_sql(seed_lexicon.sql([row("sym.lx-yilan", "Of Serpents.", "II.13", "Updated text.")]))
        assert sql("select count(*) from public.lexicon_entries where source = 'lx-test'") == "2"
        assert sql("select meaning from public.lexicon_entries where source = 'lx-test' and locator = 'II.13'") == "Updated text."
    finally:
        sql("delete from public.entities where key = 'sym.lx-yilan'")
