"""M8: the interpretation fields a dream already carries (`objects`, `features`), opened as nodes.

The `index` job calls opened() and links each group under its own extractor, so re-indexing replaces exactly
these rows. Free text (objects, people, places, events) becomes `candidate` nodes keyed by a folded slug of
its label; the fixed vocabularies (genres, experiences) are `approved` theme nodes. A genre or experience the
dreamer corrected (journal.classification) is linked with source `user` instead of the model's guess.
A quote is kept only when the label occurs word for word in the narrative."""
import re
import unicodedata
from dataclasses import dataclass

from ..models import Dream
from ..store.entities import Node

OBJECTS = "interpret.objects@1"
FEATURES = "interpret.features@1"
USER = "user.classification@1"

GENRES = {
    "daily": ("Gündelik", "Everyday"), "fantasy": ("Fantastik", "Fantasy"), "scifi": ("Bilimkurgu", "Science fiction"),
    "romance": ("Romantik", "Romance"), "adventure": ("Macera", "Adventure"), "suspense": ("Gerilim", "Suspense"),
}
EXPERIENCES = {"lucid": ("Bilinçli rüya", "Lucid dream"), "recurring": ("Tekrarlayan rüya", "Recurring dream"),
               "nightmare": ("Kâbus", "Nightmare")}
FREE = (("people", "character", "chr"), ("places", "place", "plc"), ("events", "action", "act"))
FOLD = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c",
                      "ö": "o", "Ö": "o", "ü": "u", "Ü": "u"})


@dataclass(frozen=True)
class Opened:
    node: Node
    quote: str
    status: str  # candidate | approved


def slug(label: str) -> str:
    """Language-folded, lowercase, dash-joined; empty when nothing usable is left."""
    s = unicodedata.normalize("NFKD", label.translate(FOLD)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80].rstrip("-")


def _lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def quote(label: str, text: str) -> str:
    """The label as written in the narrative (Turkish-aware case, whole words, suffixes allowed), or empty."""
    low = _lower(text)
    if not label or len(low) != len(text):
        return ""
    m = re.search(rf"(?<!\w){re.escape(_lower(label))}", low)
    return text[m.start():m.end()] if m else ""


def _free(kind: str, prefix: str, label: str, text: str, lang: str) -> Opened | None:
    key = slug(label)
    if not key:
        return None
    return Opened(Node(kind, f"{prefix}.{key}", {lang: label.strip()}), quote(label.strip(), text), "candidate")


def _genre(g: str) -> Opened:
    tr, en = GENRES[g]
    return Opened(Node("theme", f"genre.{g}", {"tr": tr, "en": en}), "", "approved")


def _experience(kind: str, q: str) -> Opened:
    tr, en = EXPERIENCES[kind]
    return Opened(Node("theme", f"experience.{kind}", {"tr": tr, "en": en}), q, "approved")


def _unique(items: list[Opened | None]) -> list[Opened]:
    seen, out = set(), []
    for o in items:
        if o and (o.node.kind, o.node.key) not in seen:
            seen.add((o.node.kind, o.node.key))
            out.append(o)
    return out


def opened(d: Dream, lang: str) -> dict[tuple[str, str], list[Opened]]:
    """(extractor, source) -> nodes to link for this dream."""
    text, f = d.originalText, d.features
    override = d.journal.classification
    objects = _unique([_free("symbol", "sym", o.label, text, lang) for o in d.objects])
    features = [_free(kind, prefix, label, text, lang) for field, kind, prefix in FREE for label in getattr(f, field)]
    user: list[Opened | None] = []
    if override and override.genres is not None:
        user += [_genre(g) for g in override.genres]
    else:
        features += [_genre(g) for g in f.genres]
    if override and override.experiences is not None:
        quotes = {e.kind: e.quote for e in f.experiences}
        user += [_experience(k, quotes.get(k, "")) for k in override.experiences]
    else:
        features += [_experience(e.kind, e.quote) for e in f.experiences]
    return {(OBJECTS, "model"): objects, (FEATURES, "model"): _unique(features), (USER, "user"): _unique(user)}
