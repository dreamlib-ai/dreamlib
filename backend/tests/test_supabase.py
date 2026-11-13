import asyncio
import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.errors import Conflict, NotFound
from app.models import Dream, MangaMeta, Panel
from app.errors import ApiError
from app.services import UserLocks
from app.store.quota import SupabaseQuota
from app.store.supabase import Supabase, Unauthorized

UID = "0a1b2c3d-0000-4000-8000-000000000001"
DID = "0a1b2c3d-0000-4000-8000-0000000000aa"
ROW = {
    "id": DID, "user_id": UID, "title": "T", "original_text": "o", "clean_text": "c", "interpretation_type": "universal",
    "interpretation": "i", "mood": "", "sleep": "", "tags": None, "objects": None, "emotions": None, "style": "manga",
    "panels": [{"caption": "a", "path": f"{UID}/a.png"}], "visibility": "private", "created_at": "2026-10-16T10:00:00.123456+00:00",
    "manga_meta": {"Style": "manga", "CharacterNote": "n", "Scenes": ["s"], "RefURL": "", "Consistent": True},
}


def client(handler) -> Supabase:
    return Supabase("https://x.supabase.co/", "service-key", allow_http=True, transport=httpx.MockTransport(handler))


def run(coro):
    return asyncio.run(coro)


KEY = ec.generate_private_key(ec.SECP256R1())
JWK = {**json.loads(jwt.algorithms.ECAlgorithm.to_jwk(KEY.public_key())), "kid": "k1", "alg": "ES256"}


def token(sub=UID, kid="k1", key=KEY, alg="ES256", **claims) -> str:
    body = {"sub": sub, "aud": "authenticated", "iss": "https://x.supabase.co/auth/v1", "exp": int(time.time()) + 3600, **claims}
    return jwt.encode(body, key, algorithm=alg, headers={"kid": kid})


def auth_server(calls, jwks=None):
    def handler(req):
        calls.append(req.url.path)
        if req.url.path.endswith("/jwks.json"):
            return httpx.Response(200, json={"keys": jwks or []}) if jwks is not None else httpx.Response(503)
        ok = req.headers["authorization"] == f"Bearer {HS_TOKEN}"
        return httpx.Response(200, json={"id": UID}) if ok else httpx.Response(401)
    return handler


HS_TOKEN = token(key="legacy-secret-that-is-long-enough-for-hs256", alg="HS256")  # gitleaks:allow (test fixture)


def test_legacy_tokens_are_asked_of_gotrue_and_cached():
    calls = []
    sb = client(auth_server(calls, jwks=[JWK]))
    assert run(sb.user_id(HS_TOKEN)) == UID and run(sb.user_id(HS_TOKEN)) == UID
    assert calls == ["/auth/v1/user"]
    with pytest.raises(Unauthorized):
        run(sb.user_id("not a jwt"))


def test_signed_tokens_are_checked_here_against_the_published_keys():
    calls = []
    sb = client(auth_server(calls, jwks=[JWK]))
    assert run(sb.user_id(token())) == UID and not sb.is_guest(UID)
    assert run(sb.user_id(token(is_anonymous=True))) == UID and sb.is_guest(UID)
    assert calls == ["/auth/v1/.well-known/jwks.json"]  # keys fetched once, GoTrue never asked

    forged = ec.generate_private_key(ec.SECP256R1())
    for bad in (token(key=forged), token(exp=int(time.time()) - 120), token(aud="anon"), token(kid="other"), token(sub="admin")):
        with pytest.raises(Unauthorized):
            run(sb.user_id(bad))


def test_without_the_keys_gotrue_decides():
    calls = []
    sb = client(auth_server(calls, jwks=None))
    with pytest.raises(Unauthorized):  # GoTrue does not know this token
        run(sb.user_id(token()))
    assert calls == ["/auth/v1/.well-known/jwks.json", "/auth/v1/user"]


def test_rows_become_dreams_and_every_query_is_scoped_to_the_owner():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json=[ROW])

    sb = client(handler)
    d = run(sb.get_dream(UID, DID))
    assert d.tags == [] and d.panels[0].path.endswith("a.png") and d.manga_meta.consistent and d.manga_meta.scenes == ["s"]
    assert d.createdAt.year == 2026
    assert seen[0].url.params["user_id"] == f"eq.{UID}" and seen[0].url.params["id"] == f"eq.{DID}"
    with pytest.raises(NotFound):
        run(sb.get_dream(UID, "not-a-uuid"))


def test_save_sends_database_column_names_and_old_meta_keys():
    sent = []

    def handler(req):
        sent.append(json.loads(req.content))
        return httpx.Response(201, json=[ROW])

    d = Dream(title="T", originalText="o", type="universal", style="manga", visibility="private",
              panels=[Panel(caption="a", path="p", url="never stored")], manga_meta=MangaMeta(style="manga", scenes=["s"]))
    run(client(handler).save_dream(UID, d))
    row = sent[0]
    assert row["user_id"] == UID and row["interpretation_type"] == "universal" and row["original_text"] == "o"
    assert row["panels"] == [{"caption": "a", "path": "p"}] and row["manga_meta"]["Scenes"] == ["s"]
    assert "created_at" not in row and "id" not in row


def test_replace_panels_is_compare_and_swap():
    def handler(req):
        assert json.loads(req.url.params["panels"].removeprefix("eq.")) == [{"caption": "a", "path": "old"}]
        return httpx.Response(200, json=[ROW] if req.url.params["user_id"] == f"eq.{UID}" else [])

    sb = client(handler)
    before, after = [Panel(caption="a", path="old")], [Panel(caption="a", path="new")]
    run(sb.replace_panels(UID, DID, before, after, MangaMeta()))
    with pytest.raises(Conflict):
        run(sb.replace_panels("0a1b2c3d-0000-4000-8000-000000000002", DID, before, after, MangaMeta()))


def test_storage_save_sign_and_remove():
    uploads = []

    def handler(req):
        url = str(req.url)
        if url.startswith("http://fal.test/"):
            return httpx.Response(200, content=b"PNG", headers={"content-type": "image/png"})
        if "/object/sign/" in url:
            return httpx.Response(200, json=[{"path": "a", "signedURL": "/object/sign/dream-images/a?token=t"}, {"path": "b", "error": "nope", "signedURL": None}])
        if req.method == "POST":
            uploads.append(url)
            return httpx.Response(200, json={})
        return httpx.Response(200, json=[])

    sb = client(handler)
    path = run(sb.save_image(UID, "http://fal.test/i.png"))
    assert path.startswith(UID + "/") and path.endswith(".png") and uploads[0].endswith("/object/dream-images/" + path)
    assert run(sb.sign(["a", "b"])) == ["https://x.supabase.co/storage/v1/object/sign/dream-images/a?token=t", ""]
    run(sb.remove([path]))
    with pytest.raises(RuntimeError):
        run(Supabase("https://x.supabase.co", "k", transport=httpx.MockTransport(handler)).save_image(UID, "http://fal.test/i.png"))


def test_quota_and_locks_go_through_postgres_functions():
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path, json.loads(req.content) if req.content else dict(req.url.params)))
        if req.url.path.endswith("/rpc/take_call"):
            return httpx.Response(200, json=len([s for s in seen if s[1].endswith("take_call")]) <= 1)
        if req.url.path.endswith("/rpc/lock_user"):
            return httpx.Response(200, json=len([s for s in seen if s[1].endswith("lock_user")]) <= 1)
        return httpx.Response(204)

    q = SupabaseQuota(client(handler))
    assert run(q.take(UID, "text", 5, 86400)) is True and run(q.take(UID, "text", 5, 86400)) is False
    assert seen[0][2] == {"p_user": UID, "p_kind": "text", "p_limit": 5, "p_window_seconds": 86400}

    locks = UserLocks(q)

    async def hold_twice():
        async with locks.hold(UID, queue=object()):
            with pytest.raises(ApiError) as e:
                async with locks.hold(UID, queue=None):
                    pass
            assert e.value.status == 409

    run(hold_twice())
    lock_calls = [s for s in seen if "lock" in s[1]]
    assert lock_calls[0][2]["p_no_jobs"] is True and lock_calls[1][2]["p_no_jobs"] is False
    assert lock_calls[2][0] == "DELETE" and lock_calls[2][2]["token"] == "eq." + lock_calls[0][2]["p_token"]


def test_stable_record_id_ignores_insert_conflicts_then_updates_only_its_owner():
    calls = []
    def handler(req):
        calls.append(req)
        if req.method == "POST":
            assert "resolution=ignore-duplicates" in req.headers["prefer"]
            return httpx.Response(201, json=[])
        assert req.method == "PATCH" and req.url.params["id"] == f"eq.{DID}"
        return httpx.Response(200, json=[ROW] if req.url.params["user_id"] == f"eq.{UID}" else [])
    sb = client(handler)
    d = Dream(id=DID, title="T", originalText="dream")
    assert run(sb.save_dream(UID, d)).id == DID
    with pytest.raises(NotFound):
        run(sb.save_dream("another-owner", d))
    assert all("merge-duplicates" not in r.headers.get("prefer", "") for r in calls)


def test_journal_update_uses_owner_and_revision_without_touching_images():
    def handler(req):
        assert req.method == 'PATCH'
        assert req.url.params['user_id'] == f'eq.{UID}'
        assert req.url.params['id'] == f'eq.{DID}'
        body = json.loads(req.content)
        assert 'panels' not in body and 'visibility' not in body
        assert body['revision'] == int(req.url.params['revision'][3:]) + 1 and body['journal']['favorite']
        return httpx.Response(200, json=[{**ROW, **body}] if req.url.params['revision'] == 'eq.3' else [])
    sb = client(handler)
    d = Supabase._from_row({**ROW, 'revision':3, 'journal': {'favorite':True}})
    assert run(sb.update_journal(UID, d, 3)).revision == 4
    with pytest.raises(Conflict):
        run(sb.update_journal(UID, d, 2))


def test_private_profile_does_not_trust_owner_editable_storage_paths():
    def handler(req):
        assert req.url.path=='/rest/v1/profiles' and req.url.params['id']==f'eq.{UID}'
        return httpx.Response(200,json=[{'id':UID,'avatar':{'spec':{}},'avatar_path':'another-user/private.webp','avatar_revision':2}])
    result=run(client(handler).get_profile(UID))
    assert result.avatarPath=='' and result.revision==2
