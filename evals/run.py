"""Eval runner: measures a set against evals/targets.toml and prints the result table.

    python evals/run.py                                  # extract set, recorded replies, no paid call
    python evals/run.py --strict                         # exit 1 when a measured target is missed
    python evals/run.py --live --record out.jsonl        # ask the configured `extract` model (paid), keep the replies

Run it with the backend's Python (backend/.venv): replies are read with the app's own models. CI runs it
on recorded replies only (docs/llm.md, Eval). Sets live in evals/<set>/: cases.jsonl (input and the
hand coding) and recorded/*.jsonl (one model reply per case id).

Today one set, `extract`, and from it the emotion rows: the app's free emotion labels are mapped onto
the five Hall–Van de Castle classes and scored as present/absent per report. Other rows of the target
table show as not measured until their set and coding exist."""
import argparse
import asyncio
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parent
sys.path.insert(0, str(ROOT / "backend"))

HVDC = ("anger", "apprehension", "sadness", "confusion", "happiness")
MIN_PCT = 10  # an emotion the model gives less than this share of counts as absent

# Free labels (Turkish or English, any form) to HVdC classes, by word stem. Curiosity (merak) is no
# HVdC class; surprise and bewilderment are confusion, contentment and relief are happiness.
STEMS: dict[str, tuple[str, ...]] = {
    "anger": ("öfke", "kızgın", "kızgınlık", "sinir", "hiddet", "anger", "angry", "rage", "irritat", "annoy", "frustrat", "furious"),
    "apprehension": ("korku", "kork", "kaygı", "endişe", "panik", "dehşet", "tedirgin", "gerginlik", "fear", "afraid",
                     "anxi", "scared", "terror", "dread", "apprehens", "worr", "nervous", "panic"),
    "sadness": ("üzüntü", "üzgün", "hüzün", "keder", "yas", "özlem", "yalnızlık", "pişmanlık", "sad", "grief", "sorrow",
                "lonel", "melanchol", "depress", "regret", "longing"),
    "confusion": ("şaşkın", "şaşırma", "kafa karış", "karmaşa", "belirsizlik", "confus", "puzzl", "bewild", "surpris",
                  "disorient", "uncertain"),
    "happiness": ("mutlu", "sevinç", "neşe", "huzur", "coşku", "keyif", "rahatla", "ferahla", "happ", "joy", "content",
                  "delight", "relie", "peace", "elat", "excite", "bliss"),
}


def hvdc_class(label: str) -> str | None:
    text = label.casefold().strip()
    for cls, stems in STEMS.items():
        if any(text.startswith(s) or f" {s}" in text for s in stems):
            return cls
    return None


@dataclass(frozen=True)
class Target:
    name: str
    metric: str
    goal: float | None
    at_most: bool  # the result must stay at or below the goal
    set: str
    human: float | None = None
    reference: float | None = None

    def passed(self, value: float) -> bool:
        assert self.goal is not None
        return value <= self.goal if self.at_most else value >= self.goal


def load_targets(path: Path = EVALS / "targets.toml") -> list[Target]:
    out = []
    for name, t in tomllib.loads(path.read_text(encoding="utf-8")).items():
        goal = t.get("target")
        if t.get("rule") == "human_ratio" and t.get("human") is not None:
            goal = round(t["human"] * 0.9, 4)
        at_most = t["metric"] == "mape" or t.get("direction") == "max"
        out.append(Target(name, t["metric"], goal, at_most, t.get("set", ""), t.get("human"), t.get("reference")))
    return out


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass(frozen=True)
class Prediction:
    emotions: set[str]  # HVdC classes
    perspective: str  # first-person | observer | mixed | unknown


def predicted(reply: str) -> Prediction | None:
    """What a reply says; None when it cannot be read as the app's Analysis."""
    from pydantic import ValidationError

    from app.models import Analysis
    from app.services import extract_json

    try:
        analysis = Analysis.model_validate(extract_json(reply))
    except (ValueError, ValidationError):
        return None
    return Prediction({c for e in analysis.emotions if e.pct >= MIN_PCT and (c := hvdc_class(e.label))},
                      analysis.features.perspective)


def f1(cases: list[tuple[set[str], set[str]]], cls: str) -> float | None:
    tp = sum(1 for want, got in cases if cls in want and cls in got)
    fp = sum(1 for want, got in cases if cls not in want and cls in got)
    fn = sum(1 for want, got in cases if cls in want and cls not in got)
    if tp + fp + fn == 0:
        return None  # the class never came up: no evidence either way, left out of the macro average
    return 2 * tp / (2 * tp + fp + fn)


def macro_f1(cases: list[tuple[set[str], set[str]]]) -> float | None:
    scores = [s for c in HVDC if (s := f1(cases, c)) is not None]
    return sum(scores) / len(scores) if scores else None


def measure_extract(cases: list[dict], replies: dict[str, str]) -> tuple[dict[str, float], dict]:
    """Emotion rows of the extract set from model replies. A missing or unreadable reply counts as
    naming no emotion."""
    preds: dict[str, Prediction | None] = {}
    missing = unreadable = 0
    for case in cases:
        reply = replies.get(case["id"])
        if reply is None:
            missing += 1
            continue
        preds[case["id"]] = predicted(reply)
        unreadable += preds[case["id"]] is None
    results, info = score(cases, preds)
    return results, {**info, "missing": missing, "unreadable": unreadable}


def lexicon_predictions(cases: list[dict]) -> dict[str, Prediction]:
    """The lab's rule engines (app/lab/): no model, no reply files."""
    from app.lab.emotions import classes
    from app.lab.perspective import perspective

    return {c["id"]: Prediction(classes(c["text"], c["lang"]), perspective(c["text"], c["lang"])) for c in cases}


def score(cases: list[dict], preds: dict[str, Prediction | None]) -> tuple[dict[str, float], dict]:
    """Extract-set rows for the predictions per case id; a missing prediction is wrong on every row."""
    pairs: dict[str, list[tuple[set[str], set[str]]]] = {"all": [], "tr": [], "en": []}
    coded = right = 0
    for case in cases:
        got = preds.get(case["id"])
        pair = (set(case["emotions"]), got.emotions if got else set())
        pairs["all"].append(pair)
        pairs.setdefault(case["lang"], []).append(pair)
        if "perspective" in case:
            coded += 1
            right += bool(got and got.perspective == case["perspective"])
    results: dict[str, float] = {}
    if coded:
        results["perspective_accuracy"] = right / coded
    for name, value in (("emotion_presence_macro_f1", macro_f1(pairs["all"])),
                        ("emotion_sadness_f1", f1(pairs["all"], "sadness")),
                        ("emotion_positive_f1", f1(pairs["all"], "happiness"))):
        if value is not None:
            results[name] = value
    tr, en = macro_f1(pairs["tr"]), macro_f1(pairs["en"])
    if tr is not None and en is not None:
        results["emotion_tr_gap"] = max(0.0, en - tr)
    return results, {"cases": len(cases), "tr": len(pairs["tr"]), "en": len(pairs["en"]), "missing": 0, "unreadable": 0}


async def live_replies(cases: list[dict]) -> dict[str, str]:
    """Asks the `extract` task's model with the app's own instructions (paid; never in CI)."""
    from app.config import load_settings
    from app.models import Analysis
    from app.prompts import ANALYZE_SYSTEM, INTERPRETATION_HINTS
    from app.providers.openrouter import OpenRouter

    cfg = load_settings()
    llm = OpenRouter(cfg.openrouter_key, cfg.openrouter_model, cfg.openrouter_routes)
    if not llm.enabled:
        raise SystemExit("live eval needs OPENROUTER_API_KEY and a model (backend/.env)")
    system = ANALYZE_SYSTEM + "\n\n" + INTERPRETATION_HINTS["universal"]
    out = {}
    for case in cases:
        out[case["id"]] = await llm.chat([{"role": "system", "content": system}, {"role": "user", "content": case["text"]}],
                                         True, task="extract", schema=Analysis)
    return out


Claims = list[tuple[str, str]]  # (kind, quote) per experience claim


def reply_claims(reply: str) -> Claims | None:
    """The experience claims a reply makes, as the model wrote them (before the app's grounding)."""
    from pydantic import ValidationError

    from app.models import Analysis
    from app.services import extract_json

    try:
        analysis = Analysis.model_validate(extract_json(reply))
    except (ValueError, ValidationError):
        return None
    return [(e.kind, e.quote) for e in analysis.features.experiences]


def lexicon_claims(cases: list[dict]) -> dict[str, Claims]:
    from app.lab.experiences import claims

    return {c["id"]: [(e.kind, e.quote) for e in claims(c["text"])] for c in cases}


def score_quote(cases: list[dict], preds: dict[str, Claims | None]) -> tuple[dict[str, float], dict]:
    """Precision of the claimed kinds against the coding, and the share of quotes found word for word."""
    made = right = verbatim = 0
    for case in cases:
        text = " ".join(case["text"].split())
        for kind, quote in preds.get(case["id"]) or []:
            made += 1
            right += kind in case["experiences"]
            verbatim += bool(quote.strip()) and " ".join(quote.split()) in text
    results = {"experience_claim_precision": right / made, "experience_quote_verbatim": verbatim / made} if made else {}
    langs = [c["lang"] for c in cases]
    return results, {"cases": len(cases), "tr": langs.count("tr"), "en": langs.count("en"), "missing": 0,
                     "unreadable": 0, "claims": made}


def table(targets: list[Target], results: dict[str, float], only_set: str) -> tuple[str, int]:
    rows = ["| Parametre | Ölçüt | Hedef | Sonuç | Durum |", "| --- | --- | --- | --- | --- |"]
    missed = 0
    for t in targets:
        if t.set != only_set:
            continue
        goal = "—" if t.goal is None else ("≤ " if t.at_most else "≥ ") + f"{t.goal:.2f}"
        if t.name not in results:
            rows.append(f"| {t.name} | {t.metric} | {goal} | — | ölçülmedi |")
            continue
        value = results[t.name]
        ok = t.goal is None or t.passed(value)
        missed += not ok
        rows.append(f"| {t.name} | {t.metric} | {goal} | {value:.2f} | {'tuttu' if ok else 'tutmadı'} |")
    return "\n".join(rows), missed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set", default="extract", choices=["extract", "quote"])
    ap.add_argument("--recorded", type=Path, help="replies file (default: evals/<set>/recorded/sample.jsonl)")
    ap.add_argument("--live", action="store_true", help="ask the model instead of reading recorded replies (paid)")
    ap.add_argument("--record", type=Path, help="with --live: write the replies here")
    ap.add_argument("--engine", choices=["model", "lexicon"], default="model",
                    help="lexicon: the lab's rule engine instead of model replies (no files, no calls)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a measured target is missed")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a code page without ≥ and ≤

    folder = EVALS / args.set
    cases = read_jsonl(folder / "cases.jsonl")
    if args.engine == "lexicon":
        source = "lab kural motorları (app/lab/)"
        if args.set == "quote":
            results, info = score_quote(cases, lexicon_claims(cases))
        else:
            results, info = score(cases, lexicon_predictions(cases))
    else:
        if args.live:
            replies = asyncio.run(live_replies(cases))
            if args.record:
                args.record.write_text("".join(json.dumps({"id": k, "reply": v}, ensure_ascii=False) + "\n"
                                               for k, v in replies.items()), encoding="utf-8")
            source = "canlı"
        else:
            path = args.recorded or folder / "recorded" / "sample.jsonl"
            replies = {r["id"]: r["reply"] for r in read_jsonl(path)} if path.is_file() else {}
            source = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
            if not path.is_file():
                source += " (yok)"
        if args.set == "quote":
            preds = {c["id"]: reply_claims(replies[c["id"]]) for c in cases if c["id"] in replies}
            results, info = score_quote(cases, preds)
            info["missing"] = sum(c["id"] not in replies for c in cases)
            info["unreadable"] = sum(v is None for v in preds.values())
        else:
            results, info = measure_extract(cases, replies)
    text, missed = table(load_targets(), results, args.set)
    print(f"Set: {args.set} · yanıtlar: {source} · {info['cases']} örnek ({info['tr']} TR, {info['en']} EN)"
          f" · yanıtsız {info['missing']} · okunamayan {info['unreadable']}\n")
    print(text)
    return 1 if args.strict and missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
