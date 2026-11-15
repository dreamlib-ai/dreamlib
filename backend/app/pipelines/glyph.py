"""`glyph` (G1, G2): the icon of one approved symbol node, drawn once for everyone (docs/uretim.md, İkon kütüphanesi).

Queued by the index job when a dream links an approved symbol whose icon is missing or drawn with an older template
revision, at most once per node and revision; the G2 migrations queued every approved symbol once. The paper around
the object is trimmed so it fills the icon, then the picture is shrunk to a 256 px WebP and kept in the public
`glyphs` bucket as `<node id>-<revision>.webp` (a new address per revision, so no cache serves the old one); the
node's `glyph_path` and `glyph_prompt` record it. Until then the client shows its kind's general icon."""
import base64
import io

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..prompts import glyph as glyph_prompts
from .context import JobContext

FAILED = "ikon çizilemedi"
TIMEOUT = 120
SIZE = 256
WORK = 384  # the drawing is trimmed at this size
MARGIN = 0.06  # of the icon's side, left around the trimmed object
INK = 28  # how far a pixel must be from the paper colour to count as the object
CREAM = (248, 242, 230)  # every icon's paper
LIGHT, GREY = 214, 34  # a pixel this light and this close to grey is paper, whatever shade the model drew


def _ink(img: Image.Image, paper: tuple[int, int, int]) -> Image.Image:
    return ImageChops.difference(img, Image.new("RGB", img.size, paper)).convert("L").point(lambda v: 255 if v > INK else 0)


def _even(img: Image.Image) -> Image.Image:
    """Paints the light, nearly grey pixels around the object the one paper cream: the model's paper, card and
    vignette tones differ by a few shades and would otherwise show as a box. Only what the picture's edge reaches
    is paper; a pale fill inside the object's outline (a loaf, a page) stays."""
    r, g, b = img.split()
    low = ImageChops.darker(ImageChops.darker(r, g), b)
    high = ImageChops.lighter(ImageChops.lighter(r, g), b)
    light = low.point(lambda v: 255 if v >= LIGHT else 0)
    grey = ImageChops.subtract(high, low).point(lambda v: 255 if v <= GREY else 0)
    paper = ImageChops.multiply(light, grey)
    w, h = paper.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if paper.getpixel(corner) == 255:
            ImageDraw.floodfill(paper, corner, 128)
    out = img.copy()
    out.paste(CREAM, mask=paper.point(lambda v: 255 if v == 128 else 0))
    return out


def fill(img: Image.Image) -> Image.Image:
    """Crops the paper around the object and centres it on a cream square with a thin margin. A model that draws
    the object on a card inside a coloured frame gets the frame (whatever touches a corner) painted cream, and the
    card's few shades off the paper evened to it."""
    obj = img.copy()
    w, h = obj.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(obj, corner, CREAM, thresh=INK * 2)
    obj = _even(obj)
    ink = _ink(obj, CREAM).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))  # no hairline rims or specks
    box = ink.getbbox()
    if not box:
        return obj
    obj = obj.crop(box)
    side = round(max(obj.size) / (1 - 2 * MARGIN))
    out = Image.new("RGB", (side, side), CREAM)
    out.paste(obj, ((side - obj.width) // 2, (side - obj.height) // 2))
    return out


def shrink(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((WORK, WORK))  # floodfill walks pixels in Python; the icon is 256 px anyway
    img = fill(img)
    if img.width == img.height:
        img = img.resize((SIZE, SIZE), Image.LANCZOS)  # a small trimmed object is scaled up too
    else:
        img.thumbnail((SIZE, SIZE))
    out = io.BytesIO()
    img.save(out, "WEBP", quality=88)
    return out.getvalue()


async def run(ctx: JobContext) -> None:
    s, job, st = ctx.s, ctx.job, ctx.state
    node = await s.entities.get(job.input["entityId"]) if s.entities else None
    if not node or node["status"] != "approved" or node["kind"] != "symbol":
        st["skipped"] = "not an approved symbol"
        return
    if node.get("glyph_path") and node.get("glyph_prompt") == glyph_prompts.LATEST:
        st["skipped"] = "already drawn"
        return
    if "request" not in st:
        labels = node.get("labels") or {}
        st["prompt_version"] = glyph_prompts.LATEST
        text = glyph_prompts.prompt(labels.get("en") or labels.get("tr") or node["key"], st["prompt_version"], node["key"])
        reference = glyph_prompts.REFERENCE
        if reference.is_file() and s.editor:
            client = s.editor
            body = client.edit_body(text, ["data:image/png;base64," + base64.b64encode(reference.read_bytes()).decode()])
        else:
            client = s.images
            body = client.image_body(text, 1)
        st.update(request=await client.submit(body), edit=client is s.editor)
        job.cost_usd += client.price
        await ctx.save()
    client = s.editor if st.get("edit") else s.images
    try:
        url = (await client.images(st["request"]))[0]
    except Exception:
        del st["request"]  # the next try asks again rather than waiting on a failed request
        await ctx.save()
        raise
    version = st["prompt_version"]
    if s.blobs and hasattr(s.blobs, "put_public"):
        name = f"{node['id']}-{version.replace('@', '')}.webp"
        path = await s.blobs.put_public("glyphs", name, shrink(await s.blobs.fetch(url)), "image/webp")
    else:
        path = url  # local work without storage: the remote picture itself
    await s.entities.set_glyph(node["id"], path, version)
    st["glyphPath"] = path
    job.done = 1


async def queue(s, user_id: str, entity_ids: list[str]) -> None:
    """One glyph job per node and template revision; a node already queued or drawn with it is not queued again."""
    from ..store.jobstore import Busy, Duplicate
    for entity_id in entity_ids:
        try:
            await s.queue.create(user_id, "glyph", {"entityId": entity_id}, 1,
                                 dedupe_key=f"glyph:{entity_id}:{glyph_prompts.LATEST}")
            s.wake()
        except (Duplicate, Busy):
            pass
