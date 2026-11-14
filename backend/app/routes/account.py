"""R2: the dreamer takes all their data with them, or deletes the account and everything in it.

Deleting removes the stored files first (nothing points at them once the rows are gone), then the auth user; every
table that holds their data is `on delete cascade`, usage rows only lose the link (`on delete set null`)."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from ..contract import AccountDelete, answers
from ..errors import ApiError
from ..services import Services, current_user, services, sign_panels

log = logging.getLogger("dreamlib")
router = APIRouter()
EXPORT_TABLES = {  # table -> columns; derived rows too, they are about the dreamer
    "consents": "dream_id,scope,text_version,granted_at,withdrawn_at",
    "magazines": "dream_id,visibility,spec,created_at,updated_at",
    "analyses": "dream_id,pipeline,prompt,model,output,created_at",
}


@router.get("/account/export", responses={200: {"description": "Bütün verilerin tek JSON dosyası"}})
async def export_account(user_id: str = Depends(current_user), s: Services = Depends(services)):
    """One JSON file: profile, every dream with its journal, consents, magazines and readings. Picture addresses
    in it are signed and work for an hour."""
    try:
        dreams, before = [], None
        while True:
            page = await s.store.list_dreams(user_id, limit=500, before=before)
            dreams += page
            if len(page) < 500:
                break
            before = (page[-1].createdAt, page[-1].id)
        await sign_panels(s, [d.panels for d in dreams])
        profile = await s.store.get_profile(user_id)
        tables = {t: await s.store.rows_of(user_id, t, cols) for t, cols in EXPORT_TABLES.items()}
    except Exception:
        log.exception("export failed")
        raise ApiError(502, "veriler hazırlanamadı")
    now = datetime.now(timezone.utc)
    body = {"exportedAt": now.isoformat(), "account": user_id, "profile": profile.model_dump(mode="json"),
            "dreams": [d.public() for d in dreams], **tables}
    name = f"dreamlib-{now.date().isoformat()}.json"
    return JSONResponse(body, headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


@router.delete("/account", status_code=204, **answers(None, 204))
async def delete_account(body: AccountDelete, user_id: str = Depends(current_user), s: Services = Depends(services)):
    """Deletes the account and everything in it; `confirm` must be "delete" so a stray request cannot."""
    try:
        files = await s.store.files_of(user_id)
        if files and s.blobs:
            for i in range(0, len(files), 500):
                await s.blobs.remove(files[i:i + 500])
        await s.store.delete_account(user_id)
    except Exception:
        log.exception("account delete failed")
        raise ApiError(502, "hesap silinemedi; tekrar dene")
    log.info("account deleted (%d files)", len(files))
    return Response(status_code=204)
