"""G3: what the library and magazine need to lay a picture out before it loads (docs/gorevler.md).

describe() reads the stored picture once with Pillow and returns its size, a BlurHash placeholder, the
dominant colour and a small WebP thumbnail. The BlurHash encoder is the published algorithm (blurha.sh),
written here so no second package is needed."""
import io
import math
from dataclasses import dataclass

from PIL import Image

THUMB = 480  # longest side of the thumbnail, px
COMPONENTS = (4, 3)  # BlurHash x, y components
B83 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~"


@dataclass(frozen=True)
class Meta:
    width: int
    height: int
    blurhash: str
    color: str  # #rrggbb
    thumb: bytes  # WebP


def _b83(value: int, length: int) -> str:
    return "".join(B83[(value // 83 ** (length - i - 1)) % 83] for i in range(length))


def _to_linear(v: int) -> float:
    c = v / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(v: float) -> int:
    c = min(1.0, max(0.0, v))
    return int(c * 12.92 * 255 + 0.5) if c <= 0.0031308 else int((1.055 * c ** (1 / 2.4) - 0.055) * 255 + 0.5)


def _sign_pow(v: float, e: float) -> float:
    return math.copysign(abs(v) ** e, v)


def blurhash(img: Image.Image, cx: int = COMPONENTS[0], cy: int = COMPONENTS[1]) -> str:
    small = img.convert("RGB").resize((32, 32), Image.Resampling.BILINEAR)
    w, h = small.size
    raw = small.tobytes()  # RGB triples, row by row
    px = [(_to_linear(raw[k]), _to_linear(raw[k + 1]), _to_linear(raw[k + 2])) for k in range(0, len(raw), 3)]
    cos_x = [[math.cos(math.pi * i * x / w) for x in range(w)] for i in range(cx)]
    cos_y = [[math.cos(math.pi * j * y / h) for y in range(h)] for j in range(cy)]
    factors = []
    for j in range(cy):
        for i in range(cx):
            norm = 1 if i == 0 and j == 0 else 2
            r = g = b = 0.0
            for y in range(h):
                for x in range(w):
                    basis = cos_x[i][x] * cos_y[j][y]
                    p = px[y * w + x]
                    r += basis * p[0]; g += basis * p[1]; b += basis * p[2]
            scale = norm / (w * h)
            factors.append((r * scale, g * scale, b * scale))
    dc, ac = factors[0], factors[1:]
    out = _b83((cx - 1) + (cy - 1) * 9, 1)
    if ac:
        actual = max(abs(c) for f in ac for c in f)
        quant = int(max(0, min(82, math.floor(actual * 166 - 0.5))))
        top = (quant + 1) / 166
        out += _b83(quant, 1)
    else:
        top = 1.0
        out += _b83(0, 1)
    out += _b83((_to_srgb(dc[0]) << 16) + (_to_srgb(dc[1]) << 8) + _to_srgb(dc[2]), 4)
    for f in ac:
        q = [int(max(0, min(18, math.floor(_sign_pow(c / top, 0.5) * 9 + 9.5)))) for c in f]
        out += _b83(q[0] * 19 * 19 + q[1] * 19 + q[2], 2)
    return out


def dominant(img: Image.Image) -> str:
    """The most common of eight colours in a small copy, as #rrggbb."""
    small = img.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR).quantize(colors=8)
    palette = small.getpalette() or []
    count, index = max(small.getcolors() or [(1, 0)])
    r, g, b = palette[index * 3: index * 3 + 3] or (0, 0, 0)
    return f"#{r:02x}{g:02x}{b:02x}"


def describe(data: bytes) -> Meta:
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        width, height = img.size
        thumb = img.convert("RGB")
        thumb.thumbnail((THUMB, THUMB), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        thumb.save(buf, "WEBP", quality=78, method=4)
        return Meta(width, height, blurhash(img), dominant(img), buf.getvalue())
