"""The eval runner (evals/run.py) on its recorded replies: CI's run of the eval, without paid calls."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("eval_run", ROOT / "evals" / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


@pytest.mark.parametrize("label, cls", [
    ("Korku", "apprehension"), ("kaygı", "apprehension"), ("anxiety", "apprehension"),
    ("özlem", "sadness"), ("grief", "sadness"), ("öfke", "anger"), ("şaşkınlık", "confusion"),
    ("huzur", "happiness"), ("joy", "happiness"), ("derin bir huzur", "happiness"),
    ("merak", None), ("utanç", None), ("", None),
])
def test_free_labels_map_onto_hvdc_classes(label, cls):
    assert run.hvdc_class(label) == cls


def test_f1_and_macro_f1_leave_out_classes_that_never_came_up():
    cases = [({"anger"}, {"anger"}), ({"sadness"}, set()), (set(), {"sadness"})]
    assert run.f1(cases, "anger") == 1.0
    assert run.f1(cases, "sadness") == 0.0
    assert run.f1(cases, "happiness") is None
    assert run.macro_f1(cases) == 0.5


def test_targets_resolve_human_ratio_and_direction(tmp_path):
    path = tmp_path / "t.toml"
    path.write_text('[a]\nmetric = "exact_agreement"\nhuman = 0.8\nrule = "human_ratio"\nset = "extract"\n'
                    '[b]\nmetric = "rate"\ntarget = 0.05\ndirection = "max"\nset = "extract"\n'
                    '[c]\nmetric = "mape"\ntarget = 0.25\nset = "production"\n', encoding="utf-8")
    a, b, c = run.load_targets(path)
    assert a.goal == 0.72 and not a.at_most and a.passed(0.72) and not a.passed(0.7)
    assert b.at_most and b.passed(0.05) and not b.passed(0.06)
    assert c.at_most


def test_every_real_target_is_readable():
    targets = run.load_targets()
    assert len(targets) > 30 and all(t.metric and t.set for t in targets)
    assert all(t.goal is not None for t in targets)


def test_recorded_extract_set_scores_as_coded_by_hand():
    cases = run.read_jsonl(ROOT / "evals/extract/cases.jsonl")
    replies = {r["id"]: r["reply"] for r in run.read_jsonl(ROOT / "evals/extract/recorded/sample.jsonl")}
    results, info = run.measure_extract(cases, replies)
    assert info == {"cases": 14, "tr": 8, "en": 6, "missing": 4, "unreadable": 1}  # 4 newer cases have no reply
    # coded HVdC-style (stated emotions only); the sample replies infer some from behaviour
    assert results["emotion_presence_macro_f1"] == pytest.approx((0 + 0.4 + 0.8 + 0.5 + 2 / 3) / 5)
    assert results["emotion_sadness_f1"] == pytest.approx(0.8)
    assert results["emotion_positive_f1"] == pytest.approx(2 / 3)
    assert results["emotion_tr_gap"] == 0.0  # Turkish did better than English here


def test_missing_and_unreadable_replies_count_as_no_emotion():
    cases = [{"id": "x", "lang": "tr", "emotions": ["sadness"]}, {"id": "y", "lang": "tr", "emotions": ["sadness"]}]
    good = json.dumps({"emotions": [{"label": "hüzün", "pct": 100}]})
    results, info = run.measure_extract(cases, {"x": good})
    assert info["missing"] == 1 and results["emotion_sadness_f1"] == pytest.approx(2 / 3)


def test_runner_prints_the_table_and_strict_fails_on_a_missed_target(capsys):
    assert run.main([]) == 0
    out = capsys.readouterr().out
    assert "| emotion_presence_macro_f1 | macro_f1 | ≥ 0.80 | 0.47 | tutmadı |" in out
    assert "| character_presence | exact_agreement | ≥ 0.84 | — | ölçülmedi |" in out
    assert "generation_eta_mape" not in out  # other sets are not listed
    assert run.main(["--strict"]) == 1
