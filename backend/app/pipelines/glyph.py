"""`glyph` (G1): the icon of one approved symbol node, drawn once for everyone (docs/uretim.md, İkon kütüphanesi).

Queued by the index job when a dream links an approved symbol that has no icon yet, at most once per node.
The picture is shrunk to a 256 px WebP and kept in the public `glyphs` bucket as `<node id>.webp`; the node's
`glyph_path` records it. Until then the client shows its kind's general icon."""
import base64
import io

from PIL import Image

from ..prompts import glyph as glyph_prompts
from .context import JobContext

FAILED = "ikon çizilemedi"
TIMEOUT = 120
SIZE = 256


def shrink(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
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
    if node.get("glyph_path"):
        st["skipped"] = "already drawn"
        return
    if "request" not in st:
        labels = node.get("labels") or {}
        st["prompt_version"] = glyph_prompts.LATEST
        text = glyph_prompts.prompt(labels.get("en") or labels.get("tr") or node["key"], st["prompt_version"])
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
    if s.blobs and hasattr(s.blobs, "put_public"):
        path = await s.blobs.put_public("glyphs", f"{node['id']}.webp", shrink(await s.blobs.fetch(url)), "image/webp")
    else:
        path = url  # local work without storage: the remote picture itself
    await s.entities.set_glyph(node["id"], path)
    st["glyphPath"] = path
    job.done = 1


async def queue(s, user_id: str, entity_ids: list[str]) -> None:
    """One glyph job per node that has none yet; a node already queued or drawn is not queued again."""
    from ..store.jobstore import Busy, Duplicate
    for entity_id in entity_ids:
        try:
            await s.queue.create(user_id, "glyph", {"entityId": entity_id}, 1, dedupe_key=f"glyph:{entity_id}")
            s.wake()
        except (Duplicate, Busy):
            pass
