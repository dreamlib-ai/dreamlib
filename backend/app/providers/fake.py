"""Stand-ins for OpenRouter and fal, so the whole app runs locally without paid keys.

Turned on with DREAMLIB_FAKE_AI=1 (together with DREAMLIB_DEV_AUTH=1 for accounts). Answers are
deterministic and built from the dream text, good enough to click through every screen; they say
nothing true about the dream. Never in production."""
import base64
import hashlib
import json
import re

from .fal import Fal

STOPWORDS = {
    "ve", "bir", "bu", "da", "de", "ile", "ama", "çok", "gibi", "sonra", "için", "ben", "beni", "bana", "o", "onu",
    "the", "and", "a", "an", "of", "to", "in", "i", "was", "my", "me", "it", "on", "with", "then",
}
PLACEHOLDER_PREFIX = "data:image/svg+xml;base64,"
PALETTE = ["#2457C5", "#102343", "#F3C84B", "#7A8CF0", "#C9D8F5", "#3B2F6B"]


def _words(text: str) -> list[str]:
    seen: list[str] = []
    for w in re.findall(r"[^\W\d_]{4,}", text.lower()):
        if w not in STOPWORDS and w not in seen:
            seen.append(w)
    return seen


def _clean(text: str) -> str:
    text = " ".join(text.split())
    return text[:1].upper() + text[1:] if text else text


def _analysis(text: str) -> dict:
    words = _words(text) or ["rüya"]
    title = " ".join(words[:2]).capitalize()
    return {
        "title": title,
        "cleanText": _clean(text),
        "tags": words[:5],
        "mood": "meraklı",
        "interpretation": "Bu, yerel deneme için üretilmiş örnek bir yorumdur; gerçek bir model çalışmadı. "
        f"Anlatımda öne çıkan sözcükler: {', '.join(words[:3])}.",
        "objects": [{"label": w, "meaning": "örnek anlam"} for w in words[:3]],
        "emotions": [{"label": "merak", "pct": 60, "note": "örnek"}, {"label": "huzur", "pct": 40, "note": "örnek"}],
        "features": {"version": 1, "genres": ["daily"], "perspective": "first-person", "people": [], "places": [], "events": [], "experiences": []},
    }


def _storyboard(text: str, n: int) -> dict:
    words = _words(text) or ["rüya"]
    return {
        "characterNote": "a calm dreamer in a soft coat",
        "panels": [{"caption": f"Sahne {i + 1}: {words[i % len(words)]}", "scene": f"a dreamlike scene about {words[i % len(words)]}"} for i in range(n)],
    }


class FakeLLM:
    """Recognises the task from the system prompt (clean, interpret, storyboard) and answers in its JSON shape."""

    enabled = True
    model = "fake"

    async def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        system, user = messages[0]["content"], messages[-1]["content"]
        if "metin düzelticisisin" in system:
            return json.dumps({"cleanText": _clean(user), "language": "tr"}, ensure_ascii=False)
        if "storyboard" in system:
            m = re.search(r"(\d+) panellik", system)
            return json.dumps(_storyboard(user, int(m.group(1)) if m else 4), ensure_ascii=False)
        return json.dumps(_analysis(user), ensure_ascii=False)


def placeholder(seed: str) -> str:
    """A small SVG picture as a data URI: a colour field with a moon whose place depends on seed."""
    h = hashlib.sha256(seed.encode()).digest()
    bg, moon = PALETTE[h[0] % len(PALETTE)], PALETTE[(h[1] + 2) % len(PALETTE)]
    x, y = 120 + h[2] % 272, 120 + h[3] % 272
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
        f'<rect width="512" height="512" fill="{bg}"/><circle cx="{x}" cy="{y}" r="64" fill="{moon}"/></svg>'
    )
    return PLACEHOLDER_PREFIX + base64.b64encode(svg.encode()).decode()


class FakeFal:
    """Queues instantly and returns placeholder pictures; transcription returns a fixed sentence."""

    enabled = True
    price = 0.0
    image_body, edit_body = staticmethod(Fal.image_body), staticmethod(Fal.edit_body)

    def __init__(self, model: str = "fake"):
        self.model = model

    async def submit(self, body: dict) -> dict:
        n = int(body.get("num_images", 1))
        return {"urls": [placeholder(f"{body.get('prompt', '')}-{i}") for i in range(n)]}

    async def images(self, handle: dict, wait_for: float = 0) -> list[str]:
        return handle["urls"]

    async def transcribe(self, audio: bytes, content_type: str, language: str = "") -> str:
        return "Dün gece denizin kıyısında yürüyordum, gökyüzünde iki ay vardı."
