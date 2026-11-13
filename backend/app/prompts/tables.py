"""The small lookup tables the routes validate against."""

# Legacy API interpretation modes; the UI uses universal without a chooser.
INTERPRETATION_HINTS = {
    "universal": "Evrensel sembolizm ve yaygın rüya tabiri geleneğine göre yorumla.",
    "cultural": "Kültürel ve dini rüya tabiri geleneklerine (ör. Anadolu ve İslami tabir) göre yorumla; yorumun hangi geleneğe dayandığını belirt.",
    "psychoanalytic": "Psikanalitik bakışla (Freud, Jung) yorumla: bilinçdışı, arketipler, bastırılmış duygular.",
}

# One request word picks the look; this prefixes the fal prompt.
STYLE_HINTS = {
    "manga": "Black and white manga panel, ink linework, screentone shading, dreamlike atmosphere",
    "illustration": "Soft editorial illustration, flat colors with print texture, surreal dreamlike mood",
    "collage": "Surreal paper collage, cut-out shapes, muted palette, dreamlike composition",
    "photographic": "Cinematic dreamlike photograph, soft light, shallow depth of field, surreal atmosphere",
}
