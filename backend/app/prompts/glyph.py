"""The icon style (G1, G2): one template for every symbol, as numbered revisions like prompts/image.py.

A symbol's icon is drawn once and kept for everyone, so the wording is fixed by revision: change it by adding the
next revision, never by editing one. The node records the revision it was drawn with (`entities.glyph_prompt`), so
a new revision redraws the older icons. If `glyph-reference.png` sits beside this file, icons are drawn from it with
the edit model so every icon keeps its line and palette; without it the text model draws from the template alone."""
from pathlib import Path

REVISIONS: dict[str, str] = {
    "glyph@1": (
        "A small icon of {label} for a dream journal: one simple object, centered, rounded friendly silhouette, "
        "dry pastel crayon texture on plain warm cream paper, cobalt blue and soft lilac with a single touch of "
        "acid yellow, generous empty margin, no text, no letters, no frame, no shadow, no scene around it"
    ),
    "glyph@2": (
        "An app icon of {label} for a dream journal: a single {label}, large, filling the whole square frame almost "
        "edge to edge, seen from its most recognisable side, bold simple rounded silhouette that reads at a glance "
        "even when tiny, thick dry pastel crayon strokes on plain warm cream paper, cobalt blue and soft lilac with "
        "a single touch of acid yellow, flat even light, no text, no letters, no frame, no border, no shadow, "
        "no background objects, no scene"
    ),
    # glyph@2 drew half the icons on a cream card inside a coloured frame ("app icon"), wrote "Dream journal" on
    # some, and drew the bare English word for ambiguous symbols (iron as a clothes iron). The subject is now a
    # concrete depiction (SUBJECTS) and the background is named as the whole image, with no card or frame.
    "glyph@3": (
        "{label}, drawn large and centered, filling most of the image, a bold simple rounded silhouette that is "
        "recognisable at a glance even when tiny, thick dry pastel crayon strokes, cobalt blue and soft lilac with a "
        "single small touch of acid yellow. The background is one flat plain warm cream colour that covers the whole "
        "image to every edge: no card, no sheet of paper, no frame, no border, no vignette, no shadow, no ground, "
        "no other objects. No text, no letters, no words, no signature"
    ),
}
LATEST = "glyph@3"
REFERENCE = Path(__file__).with_name("glyph-reference.png")

# What to draw for a symbol whose name alone is ambiguous or abstract, by node key (glyph@3 on). Others draw
# "a single <English label>". Part of the template: change it only together with a new revision.
SUBJECTS: dict[str, str] = {
    "sym.altin": "a small stack of shiny gold coins",
    "sym.anahtar": "a single old-fashioned door key",
    "sym.anne": "the head and shoulders of a smiling mother",
    "sym.at": "a single horse standing, seen from the side",
    "sym.ates": "a bright campfire flame",
    "sym.baba": "the head and shoulders of a calm father with a short beard",
    "sym.bulut": "a single puffy cloud",
    "sym.ceset": "a still human body lying flat under a white sheet",
    "sym.cocuk": "a small child standing, seen from the front",
    "sym.dag": "a single tall mountain peak with a snowy top",
    "sym.demir": "a heavy bar of raw grey iron metal",
    "sym.deniz": "a large rolling sea wave",
    "sym.deprem": "cracked ground split in two by an earthquake",
    "sym.dik-duvar": "a tall stone brick wall",
    "sym.dogum": "a newborn baby wrapped in a blanket",
    "sym.ekmek": "a round loaf of bread",
    "sym.el": "a single open human hand, palm forward",
    "sym.evcil-domuz": "a single pig standing, seen from the side",
    "sym.hububat": "a bundle of golden wheat ears",
    "sym.kafa": "a human head in profile",
    "sym.kagni": "a wooden ox cart with two solid wooden wheels",
    "sym.kitap": "an open book",
    "sym.kusma": "a queasy face with puffed cheeks about to vomit",
    "sym.meyve": "a single apple with a leaf",
    "sym.nikah": "two interlocked wedding rings",
    "sym.para": "a paper banknote with two coins",
    "sym.ruzgar": "swirling gusts of wind carrying a few leaves",
    "sym.sac": "a long flowing lock of hair",
    "sym.sakal": "a full beard on a man's chin and jaw, face only",
    "sym.savas-arabasi": "an ancient two-wheeled war chariot",
    "sym.sut": "a glass bottle of milk",
    "sym.yikanma": "a person washing in a bathtub full of bubbles",
    "sym.yuzuk": "a single gold ring with one gem",
}


def subject(key: str, label: str) -> str:
    return SUBJECTS.get(key) or f"a single {label}"


def prompt(label: str, version: str = LATEST, key: str = "") -> str:
    label = " ".join(label.split())[:80]
    if version not in ("glyph@1", "glyph@2"):
        label = subject(key, label)
    text = REVISIONS[version].format(label=label)
    return text[0].upper() + text[1:]
