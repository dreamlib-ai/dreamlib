"""M7: the interpret task gets the lexicon's meanings and the collective totals for the symbols the dream names."""
import asyncio

from app.lexicon import context, named
from app.store.lexicon import MemoryLexicon

from .conftest import auth

ALIASES = {"yılan": "s-yilan", "yılanlar": "s-yilan", "ırmak": "s-irmak", "iz": "s-iz", "kapı": "s-kapi"}
ENTRIES = [
    {"id": "l1", "entity_id": "s-yilan", "tradition": "greko-romen", "meaning": "If any one dreams of a serpent...",
     "meaning_tr": "", "source": "Oneirocritica", "locator": "II.13", "attributed_author": "Artemidorus"},
    {"id": "l2", "entity_id": "s-yilan", "tradition": "greko-romen", "meaning": "Of dragons.", "meaning_tr": "",
     "source": "Oneirocritica", "locator": "II.14", "attributed_author": "Artemidorus"},
    {"id": "l3", "entity_id": "s-yilan", "tradition": "greko-romen", "meaning": "A third one.", "meaning_tr": "",
     "source": "Oneirocritica", "locator": "II.15", "attributed_author": "Artemidorus"},
]
TOTALS = [{"entity_id": "s-yilan", "emotion": "hvdc.apprehension", "dreams": 7, "people": 6}]


class Services:
    def __init__(self, lexicon):
        self.lexicon = lexicon


def test_named_takes_suffixes_turkish_capitals_and_first_mention_first():
    found = named("Irmağın kıyısında YILANLARI gördüm, sonra bir kapıya vardım.", ALIASES)
    assert found == [("yılan", "s-yilan"), ("kapı", "s-kapi")]  # one name per symbol (the root), in reading order
    assert named("İzmir'de bir Irmak", {"ırmak": "s-irmak", "izmir": "s-izmir"}) == [("izmir", "s-izmir"), ("ırmak", "s-irmak")]


def test_named_matches_word_starts_and_skips_short_names():
    assert named("Biz uzun bir yolda yürüdük.", ALIASES) == []  # "iz" is too short; no match inside a word
    assert named("Sarıyılan bir şeydi.", ALIASES) == []


def test_context_block_names_sources_and_counts():
    block, used = asyncio.run(context(Services(MemoryLexicon(ALIASES, ENTRIES, TOTALS)), "Bir yılan kovaladı."))
    assert block.startswith("Sözlük ve kolektif bağlam")
    assert "- yılan (greko-romen; Artemidorus, II.13): If any one dreams" in block
    assert "II.15" not in block  # two meanings per symbol at most
    assert "en sık duygu korku ve kaygı (7 rüya, 6 kişi)" in block
    assert used == {"symbols": ["s-yilan"], "lexicon": ["l1", "l2"],
                    "collective": [{"symbol": "s-yilan", "emotion": "hvdc.apprehension", "dreams": 7}]}


def test_context_is_empty_without_a_lexicon_a_match_or_when_it_fails():
    assert asyncio.run(context(Services(None), "Bir yılan.")) == ("", {})
    assert asyncio.run(context(Services(MemoryLexicon(ALIASES, ENTRIES, TOTALS)), "Uçuyordum.")) == ("", {})

    class Broken(MemoryLexicon):
        async def aliases(self):
            raise RuntimeError("down")

    assert asyncio.run(context(Services(Broken()), "Bir yılan.")) == ("", {})


def test_analyze_puts_the_block_in_the_prompt_and_the_row(api):
    client, s = api
    s.lexicon = MemoryLexicon(ALIASES, ENTRIES, TOTALS)
    res = client.post("/api/v1/analyze", json={"text": "Bir yılan kovaladı."}, headers=auth())
    assert res.status_code == 200
    assert "Artemidorus, II.13" in s.llm.system
    if s.analyses:
        assert s.analyses.rows[-1]["output"]["context"]["symbols"] == ["s-yilan"]
