"""Manga booklets: a storyboard from the LLM, then the panels from fal.

Every step is written to the job's state as it finishes (storyboard, each queued fal request,
each stored panel), so a booklet picked up after a restart carries on from where it stopped."""
import asyncio
import logging

from ..models import MangaMeta, Panel, Storyboard
from ..prompts import STYLE_HINTS, storyboard_prompt
from ..services import Services, clip, extract_json
from ..avatar import AvatarSpec, avatar_prompt
from .context import JobContext, JobFailed, LostLease

log = logging.getLogger("dreamlib")

MANGA_TIMEOUT = 8 * 60
REDO_TIMEOUT = 3 * 60
PANEL_CONCURRENCY = 3
MAX_SCENE_PROMPT = 900
PANEL_COUNTS = {4, 6, 9}
FAILED = "bazı paneller çizilemedi, tekrar dene"  # shown when every try has failed


async def run(ctx: JobContext) -> None:
    """Writes the storyboard, draws the first panel, then the rest (a few at a time, from the first
    one when the character should stay the same) and files the pictures away."""
    s, job, st = ctx.s, ctx.job, ctx.state
    n = job.total
    if "meta" not in st:
        meta, captions = await _storyboard(s, job.input, n)
        st.update(meta=meta.model_dump(by_alias=True), captions=captions, paths=[""] * n, requests={})
        await ctx.save()
    meta = MangaMeta.model_validate(st["meta"])
    if not st['paths'][0] and meta.avatar_path:
        await avatar_reference(s,meta)
    paths, requests = st["paths"], st.setdefault("requests", {})

    async def draw(i: int) -> str:
        used_editor = meta.consistent and bool(meta.ref_url)
        path, remote = await render(s, job.user_id, meta, i, requests, ctx.save)
        requests.pop(str(i), None)
        paths[i] = path
        job.done = sum(1 for p in paths if p)
        job.cost_usd += (s.editor if used_editor else s.images).price
        await ctx.save()
        return remote

    # Panel one sets the look; its picture is the reference for the others.
    if not paths[0]:
        meta.ref_url = await draw(0)
    else:
        await refresh_reference(s, meta, [Panel(path=paths[0])])

    sem = asyncio.Semaphore(PANEL_CONCURRENCY)

    async def later(i: int) -> None:
        async with sem:
            await draw(i)

    results = await asyncio.gather(*(later(i) for i in range(1, n) if not paths[i]), return_exceptions=True)
    for r in results:
        if isinstance(r, LostLease):
            raise r
        if isinstance(r, BaseException):
            raise RuntimeError(f"panel failed: {r!r}") from r


async def _storyboard(s: Services, input: dict, n: int) -> tuple[MangaMeta, list[str]]:
    perspective = input.get('perspective','unknown')
    camera = {'first-person':'Every panel is POV through the dreamer\'s eyes; show their hands or body only if appropriate, never an outside portrait of them.', 'observer':'Show the dreamer from an external observer camera.', 'mixed':'Follow the explicitly changing viewpoint in the narrative.', 'unknown':'Follow the viewpoint in the narrative; do not impose a camera choice.'}[perspective]
    appearance = AvatarSpec.model_validate(input['avatarSpec']) if input.get('avatarSpec') else None
    system = storyboard_prompt(n) + '\nCamera direction: ' + camera
    if appearance:
        system += '\nThe dreamer uses this fixed character appearance. Preserve it; do not replace them with an unrelated character. ' + avatar_prompt(appearance)
    try:
        reply = await s.llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": f"{input.get('title', '')}\n\n{input['text']}"}], True, task="storyboard", schema=Storyboard
        )
    except Exception as e:
        raise RuntimeError(f"storyboard failed: {e}") from e  # worth another try
    try:
        sb = extract_json(reply)
        scenes = [str(p["scene"]) for p in sb["panels"]]
        captions = [str(p.get("caption", "")).strip() for p in sb["panels"]]
        if len(scenes) < n:
            raise ValueError(f"only {len(scenes)} panels")
    except (ValueError, KeyError, TypeError) as e:
        raise JobFailed("hikâye taslağı okunamadı, tekrar dene", f"bad storyboard: {e}")
    scenes = [camera + ' ' + scene for scene in scenes]
    meta = MangaMeta(style=input["style"], character_note=str(sb.get("characterNote", "")), scenes=scenes[:n], consistent=input["consistent"],avatar_path=input.get('avatarPath',''),avatar_spec=appearance,perspective=perspective)
    return meta, captions[:n]


def panels_of(st: dict) -> list[Panel]:
    """The booklet as the API shows it: a caption and a picture per panel."""
    return [Panel(caption=c, path=p) for c, p in zip(st.get("captions", []), st.get("paths", []))]


async def render(s: Services, user_id: str, meta: MangaMeta, i: int, requests: dict | None = None, save=None) -> tuple[str, str]:
    """Draws panel i and stores it; returns the storage path and the remote URL the picture came
    from. With consistency on, an edit failure fails the panel rather than quietly replacing the
    character with an unrelated text-only generation. A queued request is kept in requests (and
    saved) before waiting on it, so it can be picked up again."""
    scene, style = meta.scenes[i], STYLE_HINTS[meta.style]
    if meta.consistent and meta.ref_url:
        if not s.editor:
            raise RuntimeError("manga: editor unavailable")
        identity = 'Keep the same recognizable individual, face, hair, clothing silhouette and proportions; adapt the reference to the requested rendering style.' if i == 0 and meta.avatar_path else 'Keep the exact same character design, proportions and art style as the reference image.'
        prompt = f"{identity} {style}. New scene: {scene}"
        client, body = s.editor, s.editor.edit_body(clip(prompt, MAX_SCENE_PROMPT), [meta.ref_url])
    else:
        client, body = s.images, s.images.image_body(clip(f"{style}. {meta.character_note}. {scene}", MAX_SCENE_PROMPT))

    requests = {} if requests is None else requests
    key = str(i)
    for attempt in range(2):
        try:
            if key not in requests:
                requests[key] = await client.submit(body)
                if save:
                    await save()
            remote = (await client.images(requests[key]))[0]
            break
        except LostLease:
            raise
        except Exception as e:
            requests.pop(key, None)
            if attempt == 1:
                raise
            log.warning("manga: panel %d failed once: %s", i, e)

    if not s.blobs:
        return remote, remote
    return await s.blobs.save_image(user_id, remote), remote


async def refresh_reference(s: Services, meta: MangaMeta, panels: list[Panel]) -> None:
    """Signs the stored first panel afresh; provider URLs may have expired."""
    if not meta.consistent or not panels:
        return
    meta.ref_url = panels[0].path
    if s.blobs:
        urls = await s.blobs.sign([panels[0].path])
        if len(urls) != 1 or not urls[0]:
            raise RuntimeError("reference could not be signed")
        meta.ref_url = urls[0]


async def avatar_reference(s: Services, meta: MangaMeta) -> None:
    meta.ref_url = meta.avatar_path
    if s.blobs:
        urls = await s.blobs.sign([meta.avatar_path])
        if not urls or not urls[0]:
            raise RuntimeError('avatar reference unavailable')
        meta.ref_url = urls[0]
