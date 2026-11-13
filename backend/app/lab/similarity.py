"""Similar dreams without a model: shared words (TF-IDF) and shared codes (HVdC emotions, perspective,
experience claims), each match explained by what the two reports have in common (docs/motor.md: the
`similar` score is composite so it can be explained).

Words are cut to their first five letters, a known stand-in for a Turkish stemmer in retrieval
(koridorunda, koridorlarında → korid), and the same cut is used for English. What this cannot do:
match a Turkish report with an English one, or synonyms (deniz/okyanus); that needs vectors of meaning
(docs/lab.md, path B)."""
import math
from collections import Counter
from dataclasses import dataclass, field

from .emotions import WORD, classes, lower_tr
from .experiences import claims
from .perspective import perspective

STEM = 5
WORDS_WEIGHT, CODES_WEIGHT = 0.7, 0.3
STOP = {
    "ve", "bir", "bu", "şu", "da", "de", "ile", "ama", "çok", "gibi", "sonra", "için", "ben", "beni", "bana",
    "benim", "o", "onu", "ona", "onun", "ki", "mi", "ne", "her", "hiç", "daha", "en", "sanki", "önce", "birden",
    "the", "and", "a", "an", "of", "to", "in", "i", "was", "my", "me", "it", "on", "with", "then", "at", "as",
    "that", "had", "he", "she", "his", "her", "we", "they", "there", "were", "is", "be", "by", "from", "for",
}


def stems(text: str, lang: str = "tr") -> list[str]:
    low = lower_tr(text) if lang == "tr" else text.lower()
    return [w[:STEM] for w in WORD.findall(low) if w not in STOP and len(w) > 2]


def codes(text: str, lang: str = "tr") -> set[str]:
    out = {f"duygu:{c}" for c in classes(text, lang)}
    out |= {f"beyan:{e.kind}" for e in claims(text)}
    p = perspective(text, lang)
    if p != "unknown":
        out.add(f"bakış:{p}")
    return out


@dataclass
class Doc:
    id: str
    lang: str
    tf: Counter
    codes: set[str]


@dataclass(frozen=True)
class Match:
    id: str
    score: float
    words: float  # TF-IDF cosine
    shared_codes: float  # Jaccard of the codes
    because: list[str] = field(default_factory=list)  # shared stems by weight, then shared codes


class Library:
    """A user's (or any) set of reports, indexed once; ask for the neighbours of one of them."""

    def __init__(self, reports: list[dict]):
        self.docs = {r["id"]: Doc(r["id"], r.get("lang", "tr"), Counter(stems(r["text"], r.get("lang", "tr"))),
                                  codes(r["text"], r.get("lang", "tr"))) for r in reports}
        df = Counter(s for d in self.docs.values() for s in d.tf)
        n = len(self.docs)
        self.idf = {s: math.log((1 + n) / (1 + c)) + 1 for s, c in df.items()}

    def _vec(self, doc: Doc) -> dict[str, float]:
        return {s: (1 + math.log(c)) * self.idf[s] for s, c in doc.tf.items()}

    def neighbours(self, report_id: str, limit: int = 5) -> list[Match]:
        me = self.docs[report_id]
        mv = self._vec(me)
        mnorm = math.sqrt(sum(v * v for v in mv.values())) or 1.0
        out = []
        for other in self.docs.values():
            if other.id == report_id:
                continue
            ov = self._vec(other)
            onorm = math.sqrt(sum(v * v for v in ov.values())) or 1.0
            shared = {s: mv[s] * ov[s] for s in mv.keys() & ov.keys()}
            cos = sum(shared.values()) / (mnorm * onorm)
            union = me.codes | other.codes
            jac = len(me.codes & other.codes) / len(union) if union else 0.0
            because = [s for s, _ in sorted(shared.items(), key=lambda x: -x[1])[:5]] + sorted(me.codes & other.codes)
            out.append(Match(other.id, WORDS_WEIGHT * cos + CODES_WEIGHT * jac, cos, jac, because))
        return sorted(out, key=lambda m: (-m.score, m.id))[:limit]
