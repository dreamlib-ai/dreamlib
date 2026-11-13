import pytest

from app.classification import ExperienceEvidence, Features, grounded_features
from app.lab.experiences import claims
from app.lab.perspective import perspective, read


@pytest.mark.parametrize("text, lang, want", [
    ("Eski evimize gittim ve kapıyı açtım.", "tr", "first-person"),
    ("Koşuyordum, sonra düşmüştüm.", "tr", "first-person"),
    ("Kendimi dışarıdan izliyordum, sanki bir film.", "tr", "observer"),
    ("Bir adam denize atladı, kadın onu kurtarmak için koştu ve herkes bağırıyordu.", "tr", "observer"),
    ("Önce kendimi uzaktan izledim. Sonra koşmaya başladım.", "tr", "mixed"),
    ("Yardım istedi.", "tr", "unknown"),  # yardım is a noun, and too short to call
    ("I opened the door and walked in.", "en", "first-person"),
    ("I was watching myself from the ceiling.", "en", "observer"),
    ("A man ran across the field while the children laughed together under a red sky.", "en", "observer"),
])
def test_perspective(text, lang, want):
    assert perspective(text, lang) == want


def test_possessives_are_not_first_person_verbs():
    assert read("Ayaklarım yere gömülüyordu, arkadaşlarım kıyıdaydı.").first_person == []


def test_perspective_keeps_its_evidence():
    r = read("Kendimi yukarıdan izliyordum. Sonra koşmaya başladım.")
    assert r.perspective == "mixed" and r.observer == ["kendimi yukarıdan"] and r.first_person == ["başladım"]


def test_claims_quote_the_sentence_and_skip_denials():
    text = "Yine aynı rüyayı gördüm. Rüyada olduğumu fark ettim! Ama bu bir kâbus değildi."
    got = [(e.kind, e.quote) for e in claims(text)]
    assert got == [("recurring", "Yine aynı rüyayı gördüm."), ("lucid", "Rüyada olduğumu fark ettim!")]


def test_claims_pass_the_apps_own_grounding():
    text = "I knew I was dreaming, so I flew. It was a nightmare though."
    found = claims(text)
    assert [e.kind for e in found] == ["lucid", "nightmare"]
    assert [e.kind for e in grounded_features(Features(experiences=found), text).experiences] == ["lucid", "nightmare"]


def test_english_lucid_claim_survives_turkish_lower_casing():
    # normalized() turns I into ı; before has_marker() an English lucid quote could never be accepted
    text = "I realized I was dreaming and the sky turned green."
    claim = ExperienceEvidence(kind="lucid", quote="I realized I was dreaming")
    assert [e.kind for e in grounded_features(Features(experiences=[claim]), text).experiences] == ["lucid"]


def test_no_claim_without_a_marker():
    assert claims("Uçuyordum ve çok mutluydum.") == []
