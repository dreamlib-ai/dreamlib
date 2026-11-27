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
    # image@2: a live flux test drew a made-up signature on the first panel; panels now forbid any lettering.
    "image@2": {
        "styles": {
            "manga": "Black and white manga panel, ink linework, screentone shading, dreamlike atmosphere",
            "illustration": "Soft editorial illustration, flat colors with print texture, surreal dreamlike mood",
            "collage": "Surreal paper collage, cut-out shapes, muted palette, dreamlike composition",
            "photographic": "Cinematic dreamlike photograph, soft light, shallow depth of field, surreal atmosphere",
        },
        "single": "{style}, no text, lettering, signature or watermark. {prompt}",
        "avatar_edit": "Keep this individual recognizable while applying the requested appearance changes. {prompt}",
        "text_panel": "{style}, no text, lettering, speech bubbles, signature or watermark. {character}. {scene}",
        "edit_panel": "{identity} {style}, no text, lettering, speech bubbles, signature or watermark. New scene: {scene}",
        "identity_avatar": "Keep the same recognizable individual, face, hair, clothing silhouette and proportions; adapt the reference to the requested rendering style.",
        "identity_reference": "Keep the exact same character design, proportions and art style as the reference image.",
    },
}

REVISIONS["image@3"] = {
    **REVISIONS["image@2"],
    "identity_avatar_pov": "Use the avatar only for clothing and hands when visible; the camera is the dreamer's eyes. Do not show the avatar's face or an external portrait.",
    "styles": {
        **REVISIONS["image@2"]["styles"],
        "photographic": "Realistic dream photograph, natural light and skin, physical textures, believable lens and depth. Keep impossible elements from the story",
        "manga": "Strict monochrome manga in black ink on white paper, expressive linework and screentone shadows. Translate any color descriptions into gray values only",
        "illustration": "Hand-drawn editorial illustration for a printed magazine, shapes blocked in flat muted gouache, visibly hand-painted edges and textured paper, simplified perspective",
        "watercolor": "Hand-painted transparent watercolor on cold-pressed cotton paper, flowing pigments, wet edges, areas of untouched paper and gentle color blooms",
        "stop_motion": "Frame from a handcrafted 3D stop-motion miniature, clay and felt figures, tangible set materials, dimensional practical lighting, slight handmade irregularities",
    },
}

LATEST = "image@3"
LEGACY = "image@1"  # jobs saved before revisions were recorded used this wording
PRE_SELECTION = "image@2"  # jobs queued before the API captured the revision


def active(style: str = "") -> str:
    """The revision new jobs start with."""
    chosen = os.environ.get("DREAMLIB_IMAGE_PROMPT") or LATEST
    if chosen not in REVISIONS:
        raise ValueError(f"DREAMLIB_IMAGE_PROMPT={chosen!r} is not a revision in prompts/image.py")
    return LATEST if style and style not in REVISIONS[chosen]["styles"] else chosen


def revision(version: str = "") -> dict:
    """The templates of a revision; an unknown or empty one falls back to the legacy wording."""
    return REVISIONS.get(version or LEGACY, REVISIONS[LEGACY])


STYLE_HINTS = REVISIONS[LATEST]["styles"]  # the style words requests may name
