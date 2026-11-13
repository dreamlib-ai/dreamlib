import importlib.util
from pathlib import Path

import pytest

from app.lab.emotions import EN, HVDC, TR, classes, detect

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("text, want", [
    ("Çok korktum.", {"apprehension"}),
    ("Korkmuştum ama sonra rahatladım.", {"apprehension", "happiness"}),  # -mış is not a negation
    ("Hiç korkmadım.", set()),
    ("Korkmuyordum, sadece şaşırdım.", {"confusion"}),
    ("Huzursuzdum.", {"apprehension"}),  # huzursuz is not huzur
    ("Mutsuzdum.", {"sadness"}),  # mutsuz is not mutlu
    ("KORKTUM, İÇİM BURKULDU", {"apprehension", "sadness"}),  # Turkish upper case
    ("Onu çok özlemişim.", {"sadness"}),
    ("Kızım bahçede üzüm topluyordu.", set()),  # kız (girl) and üzüm (grape) are not feelings
    ("Kafam karıştı, nerede olduğumu anlayamadım.", {"confusion"}),
])
def test_turkish(text, want):
    assert classes(text, "tr") == want


@pytest.mark.parametrize("text, want", [
    ("I was terrified.", {"apprehension"}),
    ("I was not afraid at all.", set()),
    ("I wasn't angry, just confused.", {"confusion"}),
    ("I felt sick with worry.", {"apprehension"}),
    ("She was sadly gone and I felt alone.", {"sadness"}),
    ("I saddled the horse.", set()),  # 'sad' only as sad, sadly, sadness
    ("I was unhappy.", {"sadness"}),  # not happiness
    ("Pure joy, a joyful day.", {"happiness"}),
])
def test_english(text, want):
    assert classes(text, "en") == want


def test_hits_carry_their_evidence():
    text = "Önce korkmadım, sonra çok sevindim."
    hits = detect(text)
    assert [(h.word, h.cls, h.negated) for h in hits] == [("korkmadım", "apprehension", True), ("sevindim", "happiness", False)]
    assert text[hits[1].start:].startswith("sevindim")


def test_word_lists_only_use_hvdc_classes():
    assert set(TR) == set(EN) == set(HVDC)


def test_runner_scores_the_lexicon_engine(capsys):
    spec = importlib.util.spec_from_file_location("eval_run_lab", ROOT / "evals" / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    assert run.main(["--engine", "lexicon"]) == 0
    out = capsys.readouterr().out
    assert "lab sözlük motoru" in out and "| emotion_sadness_f1 | f1 | ≥ 0.70 | 1.00 | tuttu |" in out
