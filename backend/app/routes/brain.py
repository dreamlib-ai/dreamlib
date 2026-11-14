"""BG2: the dreamer's brain graph in one answer: every dream as a node, the scored links between them (BG1)."""
import logging

from fastapi import APIRouter, Depends

from ..contract import BrainOut, answers
from ..engine.relations import RELATIONS
from ..errors import ApiError
from ..services import Services, current_user, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()


@router.get("/brain", **answers(BrainOut, 200))
async def brain(user_id: str = Depends(current_user), s: Services = Depends(services)):
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
    links = [{"relation": e["relation"], "source": e["source_id"], "target": e["target_id"], "weight": e["weight"],
              "evidence": e.get("evidence") or {}} for e in edges
             if e["source_id"] in known and e["target_id"] in known]
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
    return {"relations": list(RELATIONS), "dreams": dreams, "links": links}
