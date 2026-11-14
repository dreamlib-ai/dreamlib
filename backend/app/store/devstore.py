"""An in-memory stand-in for Supabase so the app runs locally without a database.
Data is lost on restart. Enabled only by DREAMLIB_DEV_AUTH=1."""
import secrets
from datetime import datetime, timezone

from ..errors import Conflict, NotFound
from ..models import Dream, MangaMeta, Panel
from ..avatar import SelfProfile
from .supabase import Unauthorized


class DevStore:
    def __init__(self):
        self.dreams: dict[str, list[Dream]] = {}  # user -> dreams
        self.profiles: dict[str, SelfProfile] = {}

    async def get_profile(self, user_id: str) -> SelfProfile:
        return self.profiles.get(user_id, SelfProfile(id=user_id)).model_copy(deep=True)

    async def update_profile(self, user_id: str, profile: SelfProfile, revision: int) -> SelfProfile:
        before = await self.get_profile(user_id)
        if before.revision != revision:
            raise Conflict()
        saved = profile.model_copy(deep=True,update={'id':user_id,'revision':revision+1})
        self.profiles[user_id] = saved
        return saved.model_copy(deep=True)

    async def user_id(self, token: str) -> str:
        """Accepts tokens of the form 'dev-<anything>' and uses the token as the user."""
        if not token.startswith("dev-") or len(token) < 12:
            raise Unauthorized()
        return token

    def is_guest(self, user_id: str) -> bool:
        """'dev-guest-…' tokens play anonymous users."""
        return user_id.startswith("dev-guest-")

    async def save_dream(self, user_id: str, d: Dream) -> Dream:
        if d.id:
            for owner, dreams in self.dreams.items():
                for index, prior in enumerate(dreams):
                    if prior.id != d.id:
                        continue
                    if owner != user_id:
                        raise NotFound()
                    saved = d.model_copy(deep=True, update={"createdAt": prior.createdAt})
                    dreams[index] = saved
                    return saved.model_copy(deep=True)
        saved = d.model_copy(deep=True, update={"id": d.id or secrets.token_hex(8), "createdAt": datetime.now(timezone.utc)})
        self.dreams.setdefault(user_id, []).append(saved)
        return saved.model_copy(deep=True)

    async def list_dreams(self, user_id: str, limit: int = 200, exclude_id: str = "",
                          before: tuple[datetime, str] | None = None) -> list[Dream]:
        mine = sorted((d for d in self.dreams.get(user_id, []) if d.id != exclude_id), key=lambda d: (d.createdAt, d.id), reverse=True)
        if before:
            mine = [d for d in mine if (d.createdAt, d.id) < before]
        return [d.model_copy(deep=True) for d in mine[:min(max(limit, 1), 1000)]]

    async def update_journal(self, user_id: str, d: Dream, revision: int) -> Dream:
        for i, prior in enumerate(self.dreams.get(user_id, [])):
            if prior.id == d.id:
                if prior.revision != revision:
                    raise Conflict()
                saved = d.model_copy(deep=True, update={"revision": revision + 1})
                self.dreams[user_id][i] = saved
                return saved.model_copy(deep=True)
        raise NotFound()

    async def get_dream(self, user_id: str, dream_id: str) -> Dream:
        for d in self.dreams.get(user_id, []):
            if d.id == dream_id:
                return d.model_copy(deep=True)
        raise NotFound()

    async def delete_dream(self, user_id: str, dream_id: str) -> None:
        mine = self.dreams.get(user_id, [])
        for i, d in enumerate(mine):
            if d.id == dream_id:
                del mine[i]
                return
        raise NotFound()

    async def replace_panels(self, user_id: str, dream_id: str, before: list[Panel], after: list[Panel], meta: MangaMeta) -> None:
        for d in self.dreams.get(user_id, []):
            if d.id == dream_id:
                if [p.stored() for p in d.panels] != [p.stored() for p in before]:
                    raise Conflict()
                d.panels, d.manga_meta = [p.model_copy() for p in after], meta.model_copy(deep=True)
                return
        raise NotFound()
