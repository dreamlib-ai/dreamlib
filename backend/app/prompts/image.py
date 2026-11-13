"""Picture prompts as numbered revisions: the style lines and every template sent to fal.

To change wording, add a new revision (copy the latest, edit, give it the next number) instead of
editing an old one. A job records the revision it started with and keeps it on retries and panel
redraws. DREAMLIB_IMAGE_PROMPT picks the revision new jobs use (empty: LATEST), so a change can be
rolled back without a deploy of code. tests/test_prompts.py pins each revision's text."""
import os

REVISIONS: dict[str, dict] = {
    "image@1": {
        "styles": {
            "manga": "Black and white manga panel, ink linework, screentone shading, dreamlike atmosphere",
            "illustration": "Soft editorial illustration, flat colors with print texture, surreal dreamlike mood",
            "collage": "Surreal paper collage, cut-out shapes, muted palette, dreamlike composition",
            "photographic": "Cinematic dreamlike photograph, soft light, shallow depth of field, surreal atmosphere",
        },
        "single": "{style}. {prompt}",
        "avatar_edit": "Keep this individual recognizable while applying the requested appearance changes. {prompt}",
        "text_panel": "{style}. {character}. {scene}",
        "edit_panel": "{identity} {style}. New scene: {scene}",
        "identity_avatar": "Keep the same recognizable individual, face, hair, clothing silhouette and proportions; adapt the reference to the requested rendering style.",
        "identity_reference": "Keep the exact same character design, proportions and art style as the reference image.",
    },
}

LATEST = "image@1"
LEGACY = "image@1"  # jobs saved before revisions were recorded used this wording


def active() -> str:
    """The revision new jobs start with."""
    chosen = os.environ.get("DREAMLIB_IMAGE_PROMPT") or LATEST
    if chosen not in REVISIONS:
        raise ValueError(f"DREAMLIB_IMAGE_PROMPT={chosen!r} is not a revision in prompts/image.py")
    return chosen


def revision(version: str = "") -> dict:
    """The templates of a revision; an unknown or empty one falls back to the legacy wording."""
    return REVISIONS.get(version or LEGACY, REVISIONS[LEGACY])


STYLE_HINTS = REVISIONS[LATEST]["styles"]  # the style words requests may name
