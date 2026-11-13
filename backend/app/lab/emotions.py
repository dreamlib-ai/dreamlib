"""Emotions named in a dream report, as the five Hall–Van de Castle classes, without a model.

HVdC codes an emotion only when the report states it ("korktum", "I was afraid"), not when a reader
infers it from events; a word list is therefore the coding rule itself, not a shortcut. Turkish words
are matched by stem at the start of a word, so every inflection counts (kork: korktum, korkuyordum,
korkmuştum); a verb's negative suffix (korkmadım, korkmuyordum) and a -sız/-suz ending (huzursuz)
cancel it. English words are matched at the start of a word and cancelled by not/never/no/without in
the three words before, within the same clause. Each hit keeps its word and place, so a result can always be explained.

Known gaps, by design of the rule: feelings shown only through behaviour (shouting, crying) and
figurative phrases ("hiç bu kadar hafif hissetmemiştim") are not caught."""
import re
from dataclasses import dataclass

HVDC = ("anger", "apprehension", "sadness", "confusion", "happiness")

# Stems (Turkish) and word beginnings (English). Longer entries are tried first, so a more exact
# form (huzursuz, unhappy) wins over the short one inside it. Multi-word entries match as phrases.
TR: dict[str, tuple[str, ...]] = {
    "anger": ("öfke", "kızgın", "kızdım", "kızdı", "kızmış", "kızıyor", "sinirlen", "sinirli", "hiddet", "nefret",
              "çileden çık", "deliye dön"),
    "apprehension": ("kork", "kaygı", "endişe", "panik", "panikle", "dehşet", "tedirgin", "gergin", "ürk", "ürper",
                     "huzursuz", "telaş", "ödüm kop", "tüylerim diken"),
    "sadness": ("üzül", "üzgün", "üzüntü", "hüzün", "hüzünlen", "keder", "özle", "mutsuz", "pişman", "yalnızlık",
                "kendimi yalnız", "içim burkul", "kahrol"),
    "confusion": ("şaşır", "şaşkın", "kafam karış", "kafası karış", "afalla", "bocala", "anlam veremed",
                  "anlayamad", "ne olduğunu bilmiyor"),
    "happiness": ("mutlu", "sevin", "neşe", "huzur", "keyif", "coşku", "rahatla", "ferahla", "içim rahat", "heyecanlan"),
}
EN: dict[str, tuple[str, ...]] = {
    "anger": ("angry", "anger", "angri", "furious", "rage", "enraged", "annoyed", "irritat", "frustrat", "mad at", "hate"),
    "apprehension": ("afraid", "fear", "scared", "terrif", "frighten", "anxi", "worr", "nervous", "panic", "dread",
                     "uneasy", "apprehens"),
    "sadness": ("sad", "unhappy", "grief", "griev", "sorrow", "lonely", "loneli", "felt alone", "depress",
                "heartbroken", "regret", "miserable"),
    "confusion": ("confus", "puzzl", "bewild", "surpris", "disorient", "could not tell", "couldn't tell",
                  "did not know where", "didn't know where", "no idea"),
    "happiness": ("happy", "happi", "joy", "glad", "delight", "content", "reliev", "relief", "elat", "excit",
                  "cheerful", "bliss"),
}
# English entries too short to be a stem: only these endings count (sad, sadly, sadness; not saddle).
EN_WHOLE: dict[str, tuple[str, ...]] = {
    "sad": ("", "ly", "ness", "der", "dest"),
    "joy": ("", "ful", "fully", "ous"),
    "rage": ("", "d"),
    "glad": ("", "ly", "ness"),
    "hate": ("", "d"),
}
EN_NEGATORS = {"not", "never", "no", "without", "nor"}
CLAUSE_END = re.compile(r"[,.;:!?—]")  # a negation does not reach past these
TR_NEGATIVE = re.compile(r"m[aeıiuü](?!ş)")  # korkMAdım, korkMUyordum; korkmuştum (-mış) stays positive
TR_PRIVATIVE = re.compile(r"s[ıiuü]z")  # huzurSUZ, mutluSUZ: without the feeling
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


@dataclass(frozen=True)
class Hit:
    cls: str
    word: str  # as written in the report
    entry: str  # the list entry it matched
    start: int
    negated: bool


def lower_tr(text: str) -> str:
    """Turkish lower case (İ→i, I→ı) so that 'KORKTUM' and 'İçim' match their stems."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _entries(table: dict[str, tuple[str, ...]]) -> list[tuple[str, str]]:
    return sorted(((e, c) for c, es in table.items() for e in es), key=lambda x: -len(x[0]))


_TR, _EN = _entries(TR), _entries(EN)


def detect(text: str, lang: str = "tr") -> list[Hit]:
    """Every emotion word in text, negated ones included (marked)."""
    low = lower_tr(text) if lang == "tr" else text.lower()
    words = [(m.start(), m.end(), m.group()) for m in WORD.finditer(low)]
    hits: list[Hit] = []
    taken: set[int] = set()  # word indexes already explained by a longer entry
    for entry, cls in _TR if lang == "tr" else _EN:
        parts = entry.split(" ")
        for i in range(len(words) - len(parts) + 1):
            if any(i + k in taken for k in range(len(parts))):
                continue
            if any(words[i + k][2] != parts[k] for k in range(len(parts) - 1)):
                continue
            last = words[i + len(parts) - 1][2]
            if not last.startswith(parts[-1]):
                continue
            rest = last[len(parts[-1]):]
            if lang == "en" and parts[-1] in EN_WHOLE and rest not in EN_WHOLE[parts[-1]]:
                continue
            if lang == "tr":
                negated = bool(TR_NEGATIVE.match(rest) or TR_PRIVATIVE.match(rest))
            else:
                negated = False
                for j in range(i - 1, max(0, i - 3) - 1, -1):  # back through the clause, at most three words
                    if CLAUSE_END.search(low[words[j][1]:words[j + 1][0]]) or words[j][2] == "but":
                        break
                    if words[j][2] in EN_NEGATORS or words[j][2].endswith("n't"):
                        negated = True
                        break
            start = words[i][0]
            end = words[i + len(parts) - 1][1]
            hits.append(Hit(cls, text[start:end], entry, start, negated))
            taken.update(range(i, i + len(parts)))
    return sorted(hits, key=lambda h: h.start)


def classes(text: str, lang: str = "tr") -> set[str]:
    """HVdC classes stated (and not negated) in the report."""
    return {h.cls for h in detect(text, lang) if not h.negated}
