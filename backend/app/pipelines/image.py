"""Single pictures from a text prompt: one fal request for all of them, stored like panels."""
from ..prompts import STYLE_HINTS
from .context import JobContext

FAILED = "görsel şu an üretilemedi"
MAX_PROMPT = 1000
MAX_IMAGES = 4


async def run(ctx: JobContext) -> None:
    s, job, st = ctx.s, ctx.job, ctx.state
    if "request" not in st:
        prompt = f"{STYLE_HINTS[job.input['style']]}. {job.input['prompt']}"
        client = s.images
        if job.input.get('purpose') == 'avatar' and job.input.get('basePath'):
            path = job.input['basePath']
            reference = (await s.blobs.sign([path]))[0] if s.blobs else path
            if not reference or not s.editor:
                raise RuntimeError('avatar reference unavailable')
            client = s.editor
            body = client.edit_body('Keep this individual recognizable while applying the requested appearance changes. '+prompt,[reference])
        else:
            body = client.image_body(prompt,job.total)
        st.update(request=await client.submit(body), paths=[])
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
