"""BG2: the dreamer's brain graph in one answer: every dream as a node, the scored links between them (BG1)."""
import logging

from fastapi import APIRouter, Depends

from ..contract import BrainEdit, BrainOut, answers
from ..engine.relations import RELATIONS
from ..errors import ApiError, NotFound
from ..services import Services, current_user, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()


@router.get("/brain", **answers(BrainOut, 200))
async def brain(user_id: str = Depends(current_user), s: Services = Depends(services)):
    return await _brain(user_id, s)


@router.post("/brain/links", **answers(BrainOut, 200))
async def edit_brain(body: BrainEdit, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """BG4: link two of the dreamer's dreams by hand, or hide a scored link between them; answers the new graph."""
    if not s.graph or not s.store:
        raise ApiError(503, "beyin grafiği kurulu değil")
    if body.a == body.b:
        raise ApiError(400, "bir rüya kendisine bağlanamaz")
    try:
        for dream_id in (body.a, body.b):
            await s.store.get_dream(user_id, dream_id)  # 404 unless both are theirs
    except NotFound:
        raise ApiError(404, "rüya bulunamadı")
    try:
        await s.graph.mark(user_id, body.a, body.b, "series" if body.action == "link" else "hidden", body.on)
    except Exception:
        log.exception("brain: edit failed")
        raise ApiError(502, "bağ kaydedilemedi")
    return await _brain(user_id, s)


async def _brain(user_id: str, s: Services) -> dict:
    if not s.graph or not s.store:
        raise ApiError(503, "beyin grafiği kurulu değil")
    try:
        corpus = await s.graph.corpus(user_id)
        edges = await s.graph.edges(user_id)
        saved = {d.id: d for d in await s.store.list_dreams(user_id, limit=1000)}
    except Exception:
        log.exception("brain: read failed")
        raise ApiError(502, "beyin grafiği açılamadı")
    firsts = [saved[d.id].panels[:1] for d in corpus if d.id in saved and saved[d.id].panels]
    await sign_panels(s, firsts)
    known = {d.id for d in corpus}
    hidden = {(e["source_id"], e["target_id"]) for e in edges if e["relation"] == "hidden"}
    links = [{"relation": e["relation"], "source": e["source_id"], "target": e["target_id"], "weight": e["weight"],
              "evidence": e.get("evidence") or {}} for e in edges
             if e["relation"] != "hidden" and e["source_id"] in known and e["target_id"] in known
             and (e["relation"] == "series" or (e["source_id"], e["target_id"]) not in hidden)]
    degree: dict[str, int] = {}
    for l in links:
        for end in (l["source"], l["target"]):
            degree[end] = degree.get(end, 0) + 1
    dreams = []
    for d in sorted(corpus, key=lambda d: (d.dated, d.id)):
        record = saved.get(d.id)
        emotions = sorted(n.key.split(".", 1)[1] for n in d.nodes.values() if n.kind == "emotion" and n.key.startswith("hvdc."))
        dreams.append({"id": d.id, "title": record.title if record else "", "dated": d.dated.isoformat(),
                       "emotions": emotions,
                       "thumbnail": (record.panels[0].url if record and record.panels else "") or "",
                       "degree": degree.get(d.id, 0)})
    return {"relations": [*RELATIONS, "series"], "dreams": dreams, "links": links}
