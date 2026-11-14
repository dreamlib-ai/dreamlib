"""Owner-only profile and avatar selection; references never come from arbitrary client URLs."""
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from ..avatar import AvatarSpec, PRESETS, PresetId, SelfProfile, avatar_prompt
from ..errors import ApiError, Conflict
from ..services import Services, current_user, services
from .jobs import _queue, job_or_404

router = APIRouter()


async def public_profile(s: Services, profile: SelfProfile) -> dict:
    out = profile.model_dump(exclude={'avatarPath'})
    url = profile.avatarPath
    if url and s.blobs:
        signed = await s.blobs.sign([url]); url = signed[0] if signed else ''
    out['avatarUrl'] = url
    return out


@router.get('/profile')
async def get_profile(user_id: str = Depends(current_user), s: Services = Depends(services)):
    return await public_profile(s, await s.store.get_profile(user_id))


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=0)
    displayName: str | None = Field(default=None,max_length=40)
    presetId: PresetId | None = None
    avatarJobId: UUID | None = None
    clearAvatar: bool = False


@router.patch('/profile')
async def update_profile(body: ProfilePatch, user_id: str = Depends(current_user), s: Services = Depends(services)):
    if sum((body.presetId is not None,body.avatarJobId is not None,body.clearAvatar)) > 1:
        raise ApiError(400,'tek bir avatar seçimi yap')
    async with s.locks.hold(user_id,s.queue):
        profile = await s.store.get_profile(user_id)
        if profile.revision != body.revision:
            raise ApiError(409,'profil başka bir yerde değişti; yeniden açıp dene')
        if body.displayName is not None:
            profile.displayName = body.displayName.strip()
        if body.clearAvatar:
            profile.avatar,profile.avatarPath,profile.presetId = None,'',None
        if body.presetId:
            profile.avatar = PRESETS[body.presetId].model_copy()
            profile.presetId = body.presetId
            profile.avatarPath = f'https://dreamlib.cenker.dev/avatars/{body.presetId}.webp'
            if s.blobs:
                data = (Path(__file__).resolve().parent.parent/'avatar-assets'/f'{body.presetId}.webp').read_bytes()
                profile.avatarPath = await s.blobs.upload_avatar_preset(user_id,body.presetId,data)
        if body.avatarJobId:
            job = await job_or_404(s,str(body.avatarJobId),user_id)
            if job.kind != 'image' or job.input.get('purpose') != 'avatar' or job.status != 'done' or len(job.state.get('paths',[])) != 1:
                raise ApiError(409,'avatar henüz hazır değil')
            profile.avatar = AvatarSpec.model_validate(job.input['avatarSpec'])
            profile.avatarPath,profile.presetId = job.state['paths'][0],None
            # Protect the generated reference before making it active; later books may retain it.
            await s.queue.update(job.id,{'state':{**job.state,'saved':True,'savedAvatar':True}})
        try:
            profile = await s.store.update_profile(user_id,profile,body.revision)
        except Conflict:
            raise ApiError(409,'profil değişti; yeniden açıp dene')
    return await public_profile(s,profile)


class AvatarIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    spec: AvatarSpec
    requestId: UUID
    baseRevision: int = Field(ge=0)


@router.post('/avatar',status_code=202)
async def create_avatar(body: AvatarIn, user_id: str = Depends(current_user), s: Services = Depends(services)):
    if not s.images:
        raise ApiError(503,'görsel servisi kurulu değil')
    # Replaying a request retains its original reference even after a profile change.
    old = await s.queue.get(str(body.requestId),user_id)
    if old:
        if old.input.get('purpose') != 'avatar' or old.input.get('avatarSpec') != body.spec.model_dump() or old.input.get('baseRevision') != body.baseRevision:
            raise ApiError(409,'bu istek başka bir avatar için kullanılmış')
        return {'id':old.id}
    profile = await s.store.get_profile(user_id)
    if profile.revision != body.baseRevision:
        raise ApiError(409,'profil değişti; yeniden açıp dene')
    if profile.avatarPath and not s.editor:
        raise ApiError(503,'karakter tutarlılığı servisi kurulu değil')
    return await _queue(s,user_id,'image',{'purpose':'avatar','avatarSpec':body.spec.model_dump(),'baseRevision':body.baseRevision,'basePath':profile.avatarPath,'prompt':avatar_prompt(body.spec),'style':'illustration'},1,str(body.requestId))
