"""The icon style (G1): one template for every symbol, as numbered revisions like prompts/image.py.

A symbol's icon is drawn once and kept for everyone, so the wording is fixed by revision: change it by adding the
next revision, never by editing one. If `glyph-reference.png` sits beside this file, icons are drawn from it with
the edit model so every icon keeps its line and palette; without it the text model draws from the template alone."""
from pathlib import Path

REVISIONS: dict[str, str] = {
    "glyph@1": (
        "A small icon of {label} for a dream journal: one simple object, centered, rounded friendly silhouette, "
        "dry pastel crayon texture on plain warm cream paper, cobalt blue and soft lilac with a single touch of "
        "acid yellow, generous empty margin, no text, no letters, no frame, no shadow, no scene around it"
    ),
}
LATEST = "glyph@1"
REFERENCE = Path(__file__).with_name("glyph-reference.png")


def prompt(label: str, version: str = LATEST) -> str:
    return REVISIONS[version].format(label=" ".join(label.split())[:80])
