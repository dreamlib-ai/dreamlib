import importlib.util
from pathlib import Path

from app.lab.similarity import Library, codes, stems

ROOT = Path(__file__).resolve().parents[2]
REPORTS = [
    {"id": "a", "lang": "tr", "text": "Karanlık bir ormanda biri beni kovalıyordu. Çok korktum."},
    {"id": "b", "lang": "tr", "text": "Gece ormanda bir kurt peşimdeydi ve korkudan titriyordum."},
    {"id": "c", "lang": "tr", "text": "Annemle pazarda domates aldık, sonra yemek yaptık."},
    {"id": "d", "lang": "tr", "text": "Denizin dibinde yüzüyordum."},
    {"id": "e", "lang": "tr", "text": "Okyanusta derinlere daldım."},
]


def test_stems_cut_turkish_words_and_drop_stopwords():
    assert stems("Koridorlarında ve koridorunda bir kapı") == ["korid", "korid", "kapı"]


def test_codes_come_from_the_lab_readers():
    assert codes("Rüyada olduğumu fark ettim ve çok korktum.") == {"duygu:apprehension", "beyan:lucid", "bakış:first-person"}


def test_neighbours_rank_shared_words_and_codes_first_and_explain_why():
    lib = Library(REPORTS)
    best = lib.neighbours("a")[0]
    assert best.id == "b" and best.score > 0
    assert "orman" in best.because and "duygu:apprehension" in best.because


def test_synonyms_are_out_of_reach_of_words():
    # deniz/okyanus share no stem: path A cannot see it (docs/lab.md, path B)
    lib = Library(REPORTS)
    assert next(m for m in lib.neighbours("d", limit=10) if m.id == "e").words == 0.0


def test_runner_measures_the_similar_set(capsys):
    spec = importlib.util.spec_from_file_location("eval_run_similar", ROOT / "evals" / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    assert run.main(["--set", "similar", "--engine", "lexicon", "--strict"]) == 0
    out = capsys.readouterr().out
    assert "7 örnek (7 TR, 0 EN)" in out
    assert "| similar_top1_accuracy | accuracy | ≥ 0.80 | 0.86 | tuttu |" in out
    assert "| similar_mrr | rate | ≥ 0.85 | 0.90 | tuttu |" in out
