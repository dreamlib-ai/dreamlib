"""F1: the symbol card."""
from app.store.lexicon import MemoryLexicon

from .conftest import auth

ID = "6f1c1c3e-1d5b-4c55-9a3e-2b7c3f0e8a11"
ENTRIES = [{"id": f"l{i}", "entity_id": ID, "tradition": "greko-romen", "meaning": f"Meaning {i}.", "meaning_tr": "",
            "source": "Oneirocritica", "locator": f"II.{i}", "attributed_author": "Artemidorus", "license": "CC0 1.0"}
           for i in range(3)]


def test_the_card_shows_meanings_with_sources_and_how_often_the_reader_dreamt_it(api):
    client, s = api
    s.lexicon = MemoryLexicon({"yılan": ID}, ENTRIES, icons={ID: "https://x/y.webp"})
    body = client.get(f"/api/v1/entities/{ID}", headers=auth()).json()
    assert body["label"] == "yılan" and body["glyph"] == "https://x/y.webp" and body["mine"] == 0
    assert body["meanings"][0] == {"tradition": "greko-romen", "text": "Meaning 0.", "source": "Oneirocritica",
                                   "locator": "II.0", "author": "Artemidorus", "license": "CC0 1.0"}
    assert len(body["meanings"]) == 3 and "others" not in body or body.get("others") is None


def test_others_appear_only_when_the_collective_total_exists(api):
    client, s = api
    s.lexicon = MemoryLexicon({"yılan": ID}, totals=[{"entity_id": ID, "emotion": "hvdc.apprehension", "dreams": 7, "people": 6}])
    assert client.get(f"/api/v1/entities/{ID}", headers=auth()).json()["others"] == {"emotion": "hvdc.apprehension", "dreams": 7, "people": 6}


def test_unknown_symbols_and_bad_ids_are_not_found_and_the_card_needs_a_session(api):
    client, s = api
    s.lexicon = MemoryLexicon({"yılan": ID})
    assert client.get("/api/v1/entities/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404
    assert client.get("/api/v1/entities/not-an-id", headers=auth()).status_code in (400, 422)
    assert client.get(f"/api/v1/entities/{ID}").status_code == 401
