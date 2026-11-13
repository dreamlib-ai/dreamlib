"""Whose eyes the dream is seen through, without a model: first-person, observer, mixed or unknown.

Each sentence is read on its own. A sentence is an observer sentence when it says the dreamer watched
from outside ("kendimi dışarıdan izliyordum", "like watching a movie"); otherwise it is a first-person
sentence when the dreamer acts in it (Turkish first-person singular endings: gördüm, koşuyordum,
düşmüştüm, gideceğim; ben, beni, bana; English I, me, my). Only observer sentences: observer; both kinds:
mixed; only first-person: first-person. A report with neither, long enough to judge, tells of others
only, so the dreamer is an observer; a very short one stays unknown."""
import re
from dataclasses import dataclass

from .emotions import lower_tr

SENTENCE = re.compile(r"[^.!?…\n]+")
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")

OBSERVER = {
    "tr": ("kendimi dışarıdan", "kendimi yukarıdan", "kendimi izliyordum", "kendimi izledim", "kendimi seyrediyordum",
           "film izler gibi", "film izliyor gibi", "sanki bir film", "seyirci gibi", "rüyada ben yoktum", "ben yoktum",
           "dışarıdan izliyordum", "dışarıdan izledim", "uzaktan izliyordum", "uzaktan izledim"),
    "en": ("watching myself", "watched myself", "saw myself from", "like a movie", "like watching a film",
           "as if watching", "like a spectator", "i was not in the dream", "i wasn't in the dream", "from above, i saw",
           "watching from outside", "watched from outside"),
}
TR_PRONOUNS = {"ben", "beni", "bana", "benim", "bende", "benden", "kendim", "kendime"}
EN_PRONOUNS = {"i", "me", "my", "myself", "mine", "i'm", "i'd", "i've"}
# First-person singular verb endings: -dım/-tım (past, also after -mış/-yor), -yorum, -acağım. The aorist
# (-arım, -ırım) is left out: it looks like a possessive (ayaklarım, arkadaşlarım) and is rare in reports.
TR_1SG = re.compile(r"(?:[dt][ıiuü]m|yorum|[ae]c[ae]ğ[ıi]m)$")
# Nouns that end like a first-person verb.
TR_NOT_VERBS = {"yardım", "adım", "kadım", "andım", "sadım", "tadım", "ödüm", "tüm", "ürüm", "durum", "yorum",
                "kurum", "boyum", "huzurum", "zorum", "yarım", "kırım", "sırım", "harem", "kerem", "ekim",
                "kerim", "tarım", "barım"}
MIN_WORDS = 8  # fewer words than this and no dreamer: too little to say


@dataclass(frozen=True)
class Reading:
    perspective: str  # first-person | observer | mixed | unknown
    first_person: list[str]  # evidence: the words that put the dreamer in the scene
    observer: list[str]  # evidence: the observer phrases


def _first_person_words(words: list[str], lang: str) -> list[str]:
    if lang == "en":
        return [w for w in words if w in EN_PRONOUNS]
    return [w for w in words if w in TR_PRONOUNS or (len(w) > 4 and w not in TR_NOT_VERBS and TR_1SG.search(w))]


def read(text: str, lang: str = "tr") -> Reading:
    low = lower_tr(text) if lang == "tr" else text.lower()
    first, seen_from_outside = [], []
    n_first = n_observer = 0
    for sentence in SENTENCE.findall(low):
        phrases = [p for p in OBSERVER[lang] if p in sentence]
        if phrases:
            n_observer += 1
            seen_from_outside += phrases
            continue
        words = _first_person_words(WORD.findall(sentence), lang)
        if words:
            n_first += 1
            first += words
    if n_observer and n_first:
        kind = "mixed"
    elif n_observer:
        kind = "observer"
    elif n_first:
        kind = "first-person"
    else:
        kind = "observer" if len(WORD.findall(low)) >= MIN_WORDS else "unknown"
    return Reading(kind, first, seen_from_outside)


def perspective(text: str, lang: str = "tr") -> str:
    return read(text, lang).perspective
