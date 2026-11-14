"""Supabase over plain HTTP: access tokens checked against the project's public keys (GoTrue as
fallback), PostgREST to store dreams, Storage for the pictures. No SDK."""
import asyncio
import json
import logging
import re
import secrets
import time
from datetime import datetime

import httpx
import jwt

from ..errors import Conflict, NotFound
from ..imagemeta import describe
from ..models import Dream, MangaMeta, Panel
from ..avatar import SelfProfile

BUCKET = "dream-images"
MAX_IMAGE = 12 << 20
SIGNED_FOR = 3600
EXT_BY_TYPE = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
ASYMMETRIC = {"ES256", "RS256"}  # Supabase signing keys whose public half is published as JWKS
JWKS_REFRESH = 600  # seconds the public keys are kept
JWKS_RETRY = 60  # an unknown key id (a rotation) looks the keys up again at most this often
log = logging.getLogger("dreamlib")
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def thumb_path(path: str) -> str:
    """Where the 480 px WebP copy of a stored picture lives (G3)."""
    return f"{path}.t.webp"

class Unauthorized(Exception):
    pass


class Supabase:
    """Accounts, dream store and picture storage in one client."""

    def __init__(self, url: str, service_key: str, allow_http: bool = False, transport: httpx.AsyncBaseTransport | None = None,
                 public_url: str = ""):
        self.url, self.key = url.rstrip("/"), service_key
        # Where browsers reach the same project. Only differs locally, where the API container talks to the
        # gateway by its Docker name but signed picture links must open on the host (SUPABASE_PUBLIC_URL).
        self.public_url = (public_url or url).rstrip("/")
        self.allow_http = allow_http  # tests only: let save_image fetch from a plain http server
        self.http = httpx.AsyncClient(timeout=15, transport=transport)
        self.cache: dict[str, tuple[str, float]] = {}  # token -> (user id, expires): one auth call per minute, not per request
        self.guests: set[str] = set()  # anonymous users seen; they get the smaller daily limit
        self.jwks: dict = {}  # key id -> public key that signs access tokens
        self.jwks_at = float("-inf")
        self.jwks_ok = False  # the last fetch worked
        self.jwks_lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.key)

    async def _do(self, method: str, path: str, bearer: str, *, json_body=None, prefer: str = "", params=None) -> httpx.Response:
        headers = {"apikey": self.key, "Authorization": f"Bearer {bearer}"}
        if prefer:
            headers["Prefer"] = prefer
        return await self.http.request(method, self.url + path, headers=headers, json=json_body, params=params)

    # --- accounts -------------------------------------------------------

    async def user_id(self, token: str) -> str:
        """Who the access token belongs to. Tokens signed with the project's asymmetric key are
        checked here against its public keys; anything else (a legacy HS256 key, keys out of reach)
        is asked of GoTrue. A signed-out token keeps working here until it expires (an hour)."""
        claims = await self._verify_here(token)
        if claims is None:
            return await self._ask_gotrue(token)
        return self._remember(claims.get("sub", ""), bool(claims.get("is_anonymous")))

    async def _verify_here(self, token: str) -> dict | None:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise Unauthorized()
        alg, kid = header.get("alg", ""), header.get("kid", "")
        if alg not in ASYMMETRIC or not kid:
            return None
        key = await self._signing_key(kid)
        if key is None:
            return None
        try:
            return jwt.decode(token, key, algorithms=[alg], audience="authenticated", issuer=f"{self.url}/auth/v1", leeway=30)
        except jwt.PyJWTError:
            raise Unauthorized()

    async def _signing_key(self, kid: str):
        """The public key with this id, from the project's JWKS. None when the keys could not be
        fetched (GoTrue decides then); Unauthorized when they were and the id is not among them."""

        def stale() -> bool:
            age = time.monotonic() - self.jwks_at
            return age > JWKS_REFRESH or (kid not in self.jwks and age > JWKS_RETRY)

        if stale():
            async with self.jwks_lock:
                if stale():
                    self.jwks_at = time.monotonic()  # a failed fetch is not retried on every request either
                    try:
                        res = await self.http.get(self.url + "/auth/v1/.well-known/jwks.json", headers={"apikey": self.key})
                        res.raise_for_status()
                        self.jwks = {k["kid"]: jwt.PyJWK(k).key for k in res.json().get("keys", []) if k.get("kid")}
                        self.jwks_ok = True
                    except Exception:
                        log.warning("auth: jwks unavailable, asking GoTrue", exc_info=True)
                        self.jwks_ok = False
        if kid in self.jwks:
            return self.jwks[kid]
        if self.jwks_ok and self.jwks:
            raise Unauthorized()
        return None

    def _remember(self, uid: str, anonymous: bool) -> str:
        if not UUID.match(uid):
            raise Unauthorized()
        if len(self.guests) > 10000:
            self.guests.clear()  # every request marks its user again
        if anonymous:
            self.guests.add(uid)
        else:
            self.guests.discard(uid)
        return uid

    async def _ask_gotrue(self, token: str) -> str:
        hit = self.cache.get(token)
        if hit and time.monotonic() < hit[1]:
            return hit[0]
        res = await self._do("GET", "/auth/v1/user", token)
        if res.status_code in (401, 403):
            raise Unauthorized()
        if res.status_code != 200:
            raise RuntimeError(f"auth: status {res.status_code}")
        user = res.json()
        uid = self._remember(user.get("id", ""), bool(user.get("is_anonymous")))
        if len(self.cache) > 1000:
            self.cache.clear()
        self.cache[token] = (uid, time.monotonic() + 60)
        return uid

    def is_guest(self, user_id: str) -> bool:
        return user_id in self.guests

    # --- dreams ---------------------------------------------------------

    async def _rest(self, method: str, params=None, body=None, prefer: str = "") -> list[dict]:
        res = await self._do(method, "/rest/v1/dreams", self.key, json_body=body, prefer=prefer, params=params)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"rest: status {res.status_code}: {res.text.strip()}")
        return res.json() if res.content.strip() else []

    @staticmethod
    def _from_row(r: dict) -> Dream:
        meta = r.get("manga_meta")
        return Dream(
            id=r["id"], title=r["title"], originalText=r["original_text"], cleanText=r["clean_text"],
            type=r["interpretation_type"], interpretation=r["interpretation"], mood=r.get("mood") or "",
            sleep=r.get("sleep") or "", tags=r.get("tags") or [], objects=r.get("objects") or [],
            emotions=r.get("emotions") or [], style=r["style"], panels=[Panel(**p) for p in r.get("panels") or []],
            manga_meta=MangaMeta.model_validate(meta) if meta else None, visibility=r.get("visibility") or "",
            createdAt=datetime.fromisoformat(r["created_at"]) if r.get("created_at") else None,
            journal=r.get("journal") or {}, revision=r.get("revision", 0),
            features=r.get("features") or {},
        )

    async def save_dream(self, user_id: str, d: Dream) -> Dream:
        row = {
            "user_id": user_id, "title": d.title, "original_text": d.originalText, "clean_text": d.cleanText,
            "interpretation_type": d.type, "interpretation": d.interpretation, "mood": d.mood, "sleep": d.sleep,
            "tags": d.tags, "objects": [o.model_dump() for o in d.objects], "emotions": [e.model_dump() for e in d.emotions],
            "style": d.style, "panels": [p.stored() for p in d.panels], "visibility": d.visibility,
            "journal": d.journal.model_dump(mode="json"), "revision": d.revision,
            "features": d.features.model_dump(mode="json"),
        }
        if d.manga_meta:
            row["manga_meta"] = d.manga_meta.model_dump(by_alias=True)
        if d.id:
            if not UUID.match(d.id):
                raise NotFound()
            # Never merge on id with the service key: a collision must not cross owners.
            rows = await self._rest("POST", body={**row, "id": d.id}, prefer="resolution=ignore-duplicates,return=representation")
            if not rows:
                rows = await self._rest("PATCH", {"id": f"eq.{d.id}", "user_id": f"eq.{user_id}"}, body=row, prefer="return=representation")
                if not rows:
                    raise NotFound()
        else:
            rows = await self._rest("POST", body=row, prefer="return=representation")
        if len(rows) != 1:
            raise RuntimeError("save: no row returned")
        return self._from_row(rows[0])

    async def list_dreams(self, user_id: str, limit: int = 200, exclude_id: str = "") -> list[Dream]:
        params = {"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": str(min(max(limit, 1), 200))}
        if exclude_id:
            params["id"] = f"neq.{exclude_id}"
        return [self._from_row(r) for r in await self._rest("GET", params)]

    async def update_journal(self, user_id: str, d: Dream, revision: int) -> Dream:
        if not UUID.match(d.id):
            raise NotFound()
        params = {"user_id": f"eq.{user_id}", "id": f"eq.{d.id}", "revision": f"eq.{revision}"}
        body = {"title": d.title, "original_text": d.originalText, "clean_text": d.cleanText,
                "interpretation": d.interpretation, "tags": d.tags,
                "objects": [o.model_dump() for o in d.objects], "emotions": [e.model_dump() for e in d.emotions],
                "journal": d.journal.model_dump(mode="json"), "revision": revision + 1}
        body["features"] = d.features.model_dump(mode="json")
        rows = await self._rest("PATCH", params, body, prefer="return=representation")
        if not rows:
            raise Conflict()
        return self._from_row(rows[0])

    async def get_dream(self, user_id: str, dream_id: str) -> Dream:
        if not UUID.match(dream_id):
            raise NotFound()
        rows = await self._rest("GET", {"user_id": f"eq.{user_id}", "id": f"eq.{dream_id}"})
        if not rows:
            raise NotFound()
        return self._from_row(rows[0])

    async def delete_dream(self, user_id: str, dream_id: str) -> None:
        if not UUID.match(dream_id):
            raise NotFound()
        rows = await self._rest("DELETE", {"user_id": f"eq.{user_id}", "id": f"eq.{dream_id}"}, prefer="return=representation")
        if not rows:
            raise NotFound()

    async def replace_panels(self, user_id: str, dream_id: str, before: list[Panel], after: list[Panel], meta: MangaMeta) -> None:
        """Compares the original panels before updating so concurrent edits cannot be lost."""
        if not UUID.match(dream_id):
            raise NotFound()
        old = json.dumps([p.stored() for p in before], separators=(",", ":"), ensure_ascii=False)
        params = {"user_id": f"eq.{user_id}", "id": f"eq.{dream_id}", "panels": f"eq.{old}"}
        body = {"panels": [p.stored() for p in after], "manga_meta": meta.model_dump(by_alias=True)}
        rows = await self._rest("PATCH", params, body, prefer="return=representation")
        if len(rows) != 1:
            raise Conflict()

    # --- pictures -------------------------------------------------------

    async def get_profile(self, user_id: str) -> SelfProfile:
        res = await self._do('GET', '/rest/v1/profiles', self.key, params={'id': f'eq.{user_id}'})
        res.raise_for_status()
        rows = res.json()
        if not rows:
            return SelfProfile(id=user_id)
        row = rows[0]
        path = row.get('avatar_path') or ''
        # Profiles are owner-editable through PostgREST too: never sign another owner's path.
        if not path.startswith(user_id+'/') or '..' in path or len(path)>300:
            path = ''
        return SelfProfile(id=user_id, displayName=row.get('display_name') or '', avatar=(row.get('avatar') or {}).get('spec'), presetId=(row.get('avatar') or {}).get('presetId'), avatarPath=path, revision=row.get('avatar_revision',0))

    async def update_profile(self, user_id: str, profile: SelfProfile, revision: int) -> SelfProfile:
        body = {'id':user_id, 'display_name':profile.displayName, 'avatar':{'spec':profile.avatar.model_dump() if profile.avatar else None,'presetId':profile.presetId}, 'avatar_path':profile.avatarPath, 'avatar_revision':revision+1}
        rows = []
        if revision == 0:
            res = await self._do('POST','/rest/v1/profiles',self.key,json_body=body,prefer='resolution=ignore-duplicates,return=representation')
            res.raise_for_status(); rows=res.json()
        if not rows:
            res = await self._do('PATCH','/rest/v1/profiles',self.key,json_body=body,params={'id':f'eq.{user_id}','avatar_revision':f'eq.{revision}'},prefer='return=representation')
            res.raise_for_status(); rows=res.json()
        if not rows:
            raise Conflict()
        return profile.model_copy(deep=True,update={'id':user_id,'revision':revision+1})

    async def upload_avatar_preset(self, user_id: str, preset_id: str, data: bytes) -> str:
        path = f'{user_id}/avatars/{preset_id}-v1.webp'
        res = await self.http.post(f'{self.url}/storage/v1/object/{BUCKET}/{path}', content=data,
            headers={'apikey':self.key,'Authorization':f'Bearer {self.key}','Content-Type':'image/webp','x-upsert':'true'})
        res.raise_for_status()
        return path

    async def save_image(self, user_id: str, source_url: str) -> str:
        """Download the image and keep it in the private bucket under the user's folder.
        Returns the storage path, which is what gets saved with a dream."""
        if not source_url.startswith("https://") and not (self.allow_http and source_url.startswith("http://")):
            raise RuntimeError("storage: source must be https")
        src = await self.http.get(source_url, timeout=60, follow_redirects=True)
        if src.status_code != 200:
            raise RuntimeError(f"storage: source status {src.status_code}")
        data = src.content
        if len(data) > MAX_IMAGE:
            raise RuntimeError("storage: image too large")
        ctype = src.headers.get("content-type", "").split(";")[0].strip()
        if ctype not in EXT_BY_TYPE:
            raise RuntimeError(f"storage: unsupported type {ctype!r}")
        path = f"{user_id}/{secrets.token_hex(16)}{EXT_BY_TYPE[ctype]}"
        up = await self.http.post(
            f"{self.url}/storage/v1/object/{BUCKET}/{path}", content=data, timeout=60,
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": ctype},
        )
        if up.status_code // 100 != 2:
            raise RuntimeError(f"storage: upload status {up.status_code}: {up.text[:300]}")
        try:  # G3: layout facts and a thumbnail; a picture is still saved when this fails
            await self._describe(user_id, path, data)
        except Exception:
            log.warning("storage: could not describe %s", path, exc_info=True)
        return path

    async def _describe(self, user_id: str, path: str, data: bytes) -> None:
        meta = await asyncio.to_thread(describe, data)
        thumb = thumb_path(path)
        up = await self.http.post(f"{self.url}/storage/v1/object/{BUCKET}/{thumb}", content=meta.thumb, timeout=60,
                                  headers={"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "image/webp"})
        if up.status_code // 100 != 2:
            raise RuntimeError(f"storage: thumb upload status {up.status_code}")
        row = {"path": path, "user_id": user_id, "width": meta.width, "height": meta.height, "blurhash": meta.blurhash,
               "color": meta.color, "thumb_path": thumb}
        res = await self._do("POST", "/rest/v1/images", self.key, json_body=row, prefer="resolution=merge-duplicates,return=minimal")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"images: insert status {res.status_code}: {res.text[:300]}")

    async def image_meta(self, paths: list[str]) -> dict[str, dict]:
        """path -> {width, height, blurhash, color, thumb_path} for the stored pictures that have one."""
        if not paths:
            return {}
        listed = ",".join('"' + p.replace('"', "") + '"' for p in paths)
        res = await self._do("GET", "/rest/v1/images", self.key, params={
            "path": f"in.({listed})", "select": "path,width,height,blurhash,color,thumb_path"})
        if res.status_code != 200:
            raise RuntimeError(f"images: read status {res.status_code}")
        return {r["path"]: r for r in res.json()}

    async def sign(self, paths: list[str]) -> list[str]:
        """An hour-long viewable URL for each storage path, in the same order ('' when it could not be signed)."""
        if not paths:
            return []
        res = await self._do("POST", f"/storage/v1/object/sign/{BUCKET}", self.key, json_body={"expiresIn": SIGNED_FOR, "paths": paths})
        if res.status_code != 200:
            raise RuntimeError(f"storage: sign status {res.status_code}")
        by_path = {o["path"]: f"{self.public_url}/storage/v1{o['signedURL']}" for o in res.json() if not o.get("error") and o.get("signedURL")}
        return [by_path.get(p, "") for p in paths]

    async def remove(self, paths: list[str]) -> None:
        """Delete stored pictures; paths that are already gone are not an error."""
        if not paths:
            return
        res = await self._do("DELETE", f"/storage/v1/object/{BUCKET}", self.key,
                             json_body={"prefixes": paths + [thumb_path(p) for p in paths]})
        if res.status_code // 100 != 2:
            raise RuntimeError(f"storage: remove status {res.status_code}")
        listed = ",".join('"' + p.replace('"', "") + '"' for p in paths)
        await self._do("DELETE", "/rest/v1/images", self.key, params={"path": f"in.({listed})"})
