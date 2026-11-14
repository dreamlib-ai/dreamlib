"""G3: size, BlurHash, dominant colour and thumbnail of a stored picture, and how panels carry them."""
import asyncio
import io

from PIL import Image

from app.imagemeta import B83, blurhash, describe, dominant
from app.models import Panel
from app.services import Services, sign_panels


def png(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def test_a_flat_picture_has_the_textbook_hash():
    h = blurhash(Image.new("RGB", (64, 48), (200, 100, 50)))
    assert len(h) == 28 and h[0] == "L"  # 4x3 components: 1 + 1 + 4 + 2 * 11 characters
    dc = B83.index(h[2]) * 83 ** 3 + B83.index(h[3]) * 83 ** 2 + B83.index(h[4]) * 83 + B83.index(h[5])
    assert (dc >> 16, (dc >> 8) & 255, dc & 255) == (200, 100, 50)


def test_a_gradient_has_detail_and_stays_the_same_length():
    img = Image.linear_gradient("L").convert("RGB")
    h = blurhash(img)
    assert len(h) == 28 and h != blurhash(Image.new("RGB", (64, 64), (128, 128, 128)))


def test_dominant_colour_and_thumbnail():
    img = Image.new("RGB", (1024, 768), (230, 30, 40))
    img.paste((20, 40, 200), (0, 0, 200, 200))
    meta = describe(png(img, "JPEG"))
    assert (meta.width, meta.height) == (1024, 768)
    r, g, b = (int(meta.color[i:i + 2], 16) for i in (1, 3, 5))
    assert r > 180 and g < 80 and b < 80
    with Image.open(io.BytesIO(meta.thumb)) as t:
        assert t.format == "WEBP" and t.size == (480, 360)


class Blobs:
    def __init__(self):
        self.rows = {"u/a.png": {"path": "u/a.png", "width": 1024, "height": 1024, "blurhash": "L0", "color": "#102343",
                                 "thumb_path": "u/a.png.t.webp"}}

    async def sign(self, paths):
        return [f"https://cdn.test/{p}?sig" for p in paths]

    async def image_meta(self, paths):
        return {p: self.rows[p] for p in paths if p in self.rows}


def test_panels_go_out_with_their_layout_facts():
    panels = [Panel(path="u/a.png"), Panel(path="u/old.png")]
    asyncio.run(sign_panels(Services(blobs=Blobs()), [panels]))
    first, old = (p.public() for p in panels)
    assert first["width"] == 1024 and first["blurhash"] == "L0" and first["thumb"] == "https://cdn.test/u/a.png.t.webp?sig"
    assert old == {"caption": "", "path": "u/old.png", "url": "https://cdn.test/u/old.png?sig"}  # older pictures unchanged
    assert Panel(path="u/a.png", width=9).stored() == {"caption": "", "path": "u/a.png"}  # never saved with the dream
