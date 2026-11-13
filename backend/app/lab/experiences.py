"""Lucid, recurring and nightmare claims, without a model: only what the report says outright.

The markers are the app's own (classification.MARKERS), the same list that already checks a model's
claims. A claim is the sentence that holds a marker, quoted word for word, so it always passes the
app's grounding check; a sentence that denies it ("kâbus değildi", "it wasn't a nightmare") is no claim.
Precision matters more than recall here (target ≥ 0.95): a false lucid badge costs trust."""
import re

from ..classification import MARKERS, ExperienceEvidence, has_marker, normalized

SENTENCE = re.compile(r"[^.!?…\n]+[.!?…]?")
DENIALS = ("değildi", "değil", "etmedim", "bilmiyordum", "olmadı", "did not", "didn't", "wasn't", "was not",
           "not a nightmare", "never")


def claims(text: str) -> list[ExperienceEvidence]:
    out: list[ExperienceEvidence] = []
    for raw in SENTENCE.findall(text):
        quote = " ".join(raw.split())
        sentence = normalized(quote)
        if not sentence or any(d in sentence for d in DENIALS):
            continue
        for kind in MARKERS:
            if kind not in {e.kind for e in out} and has_marker(sentence, kind):
                out.append(ExperienceEvidence(kind=kind, quote=quote[:200]))
    return out
