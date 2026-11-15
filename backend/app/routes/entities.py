"""F1: the symbol card: what the lexicon's traditions say about a symbol, with their sources, in how many of the
reader's dreams it appears, and what others' consented dreams show (only from five people on, karar 0007)."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends

from ..contract import EntityOut, answers
from ..errors import ApiError
from ..services import Services, current_user, services

log = logging.getLogger("dreamlib")
router = APIRouter()
PER_SYMBOL = 12


@router.get("/entities/{entity_id}", **answers(EntityOut, 200))
async def symbol_card(entity_id: UUID, user_id: str = Depends(current_user), s: Services = Depends(services)):
    lexicon = getattr(s, "lexicon", None)
    if not lexicon:
        raise ApiError(503, "sözlük kurulu değil")
    node = await lexicon.symbol(str(entity_id))
    if not node:
        raise ApiError(404, "sembol bulunamadı")
    labels = node.get("labels") or {}
    out = {"id": node["id"], "label": labels.get("tr") or labels.get("en") or "", "glyph": node.get("glyph_path") or "",
           "meanings": [{"tradition": r["tradition"], "text": r.get("meaning_tr") or r["meaning"], "source": r["source"],
                         "locator": r.get("locator") or "", "author": r.get("attributed_author") or "",
                         "license": r.get("license") or ""}
                        for r in await lexicon.meanings([node["id"]], PER_SYMBOL)],
           "mine": await lexicon.seen(user_id, node["id"])}
    try:
        if totals := await lexicon.collective([node["id"]]):
            out["others"] = {k: totals[0][k] for k in ("emotion", "dreams", "people")}
    except Exception:
        log.warning("entities: collective unavailable", exc_info=True)
    return out
