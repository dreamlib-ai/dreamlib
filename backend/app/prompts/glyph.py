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
    # G2: glyph@1 left the object small in a wide margin, unreadable at list size. The object now fills the frame
    # and reads as a bold silhouette; the pipeline also trims the paper around it (pipelines/glyph.py).
    "glyph@2": (
        "An app icon of {label} for a dream journal: a single {label}, large, filling the whole square frame almost "
        "edge to edge, seen from its most recognisable side, bold simple rounded silhouette that reads at a glance "
        "even when tiny, thick dry pastel crayon strokes on plain warm cream paper, cobalt blue and soft lilac with "
        "a single touch of acid yellow, flat even light, no text, no letters, no frame, no border, no shadow, "
        "no background objects, no scene"
    ),
}
LATEST = "glyph@2"
REFERENCE = Path(__file__).with_name("glyph-reference.png")


def prompt(label: str, version: str = LATEST) -> str:
    return REVISIONS[version].format(label=" ".join(label.split())[:80])
