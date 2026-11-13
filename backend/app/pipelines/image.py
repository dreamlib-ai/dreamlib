"""Single pictures from a text prompt: one fal request for all of them, stored like panels."""
from ..prompts import image as image_prompts
import time

from .context import JobContext


def now() -> float:
    return time.time()

FAILED = "görsel şu an üretilemedi"
MAX_PROMPT = 1000
MAX_IMAGES = 4


async def run(ctx: JobContext) -> None:
    s, job, st = ctx.s, ctx.job, ctx.state
    if "request" not in st:
        st["prompt_version"] = st.get("prompt_version") or image_prompts.active()
        t = image_prompts.revision(st["prompt_version"])
        prompt = t["single"].format(style=t["styles"][job.input['style']], prompt=job.input['prompt'])
        client = s.images
        if job.input.get('purpose') == 'avatar' and job.input.get('basePath'):
            path = job.input['basePath']
            reference = (await s.blobs.sign([path]))[0] if s.blobs else path
            if not reference or not s.editor:
                raise RuntimeError('avatar reference unavailable')
            client = s.editor
            body = client.edit_body(t["avatar_edit"].format(prompt=prompt), [reference])
        else:
            body = client.image_body(prompt,job.total)
        st.update(request=await client.submit(body), paths=[], model=client.spec.name if hasattr(client, 'spec') else '')
        refs = len(body.get('image_urls', []))
        st["eta_at"] = now() + await client.estimate(job.total if not refs else 1, refs)
        job.cost_usd += client.price * job.total
        await ctx.save()
    try:
        client = s.editor if job.input.get('purpose') == 'avatar' and job.input.get('basePath') else s.images
        urls = await client.images(st["request"])
    except Exception:
        del st["request"]  # a failed request is not waited on again; the next try submits anew
        await ctx.save()
        raise
    for url in urls[len(st["paths"]) : job.total]:  # stored ones are skipped on a second try
        st["paths"].append(await s.blobs.save_image(job.user_id, url) if s.blobs else url)
        job.done = len(st["paths"])
        await ctx.save()
