"""M6/M7: the A-tier lexicon as the interpret task reads it: approved symbols by their Turkish names, their
meanings with sources, and the collective totals (at least five people's consented dreams)."""
import time

from .supabase import Supabase

REFRESH = 600  # seconds the alias list is kept; the lexicon changes only when it is seeded


class SupabaseLexicon:
    def __init__(self, sb: Supabase):
        self.sb = sb
        self._aliases: tuple[float, dict[str, str]] = (0.0, {})

    async def _get(self, path: str, params: dict) -> list[dict]:
        res = await self.sb._do("GET", path, self.sb.key, params=params)
        if res.status_code != 200:
            raise RuntimeError(f"lexicon: {path} status {res.status_code}")
        return res.json()

    async def aliases(self) -> dict[str, str]:
        """Turkish name (lower case) -> approved symbol id."""
        at, known = self._aliases
        if time.monotonic() - at < REFRESH and known:
            return known
        rows = await self._get("/rest/v1/entity_aliases", {"lang": "eq.tr", "select": "alias,entity_id,entities!inner(kind,status)",
                                                            "entities.kind": "eq.symbol", "entities.status": "eq.approved", "limit": "20000"})
        known = {r["alias"]: r["entity_id"] for r in rows}
        self._aliases = (time.monotonic(), known)
        return known

    async def meanings(self, entity_ids: list[str], per_symbol: int = 2) -> list[dict]:
        if not entity_ids:
            return []
        rows = await self._get("/rest/v1/lexicon_entries", {
            "entity_id": f"in.({','.join(entity_ids)})", "order": "entity_id,locator",
            "select": "id,entity_id,tradition,heading,meaning,meaning_tr,source,locator,attributed_author,license"})
        out, count = [], {}
        for r in rows:
            if count.get(r["entity_id"], 0) < per_symbol:
                count[r["entity_id"]] = count.get(r["entity_id"], 0) + 1
                out.append(r)
        return out

    async def symbol(self, entity_id: str) -> dict | None:
        """F1: an approved symbol node (id, labels, glyph_path), or None."""
        rows = await self._get("/rest/v1/entities", {"id": f"eq.{entity_id}", "kind": "eq.symbol", "status": "eq.approved",
                                                     "select": "id,labels,glyph_path"})
        return rows[0] if rows else None

    async def seen(self, user_id: str, entity_id: str) -> int:
        """F1: in how many of this person's dreams the symbol appears."""
        rows = await self._get("/rest/v1/dream_entities", {"entity_id": f"eq.{entity_id}", "dreams.user_id": f"eq.{user_id}",
                                                           "select": "dream_id,dreams!inner(user_id)", "limit": "10000"})
        return len({r["dream_id"] for r in rows})

    async def glyphs(self, entity_ids: list[str]) -> dict[str, str]:
        """G8: symbol id -> icon address, for those that have one."""
        if not entity_ids:
            return {}
        rows = await self._get("/rest/v1/entities", {"id": f"in.({','.join(entity_ids)})", "glyph_path": "neq.",
                                                     "select": "id,glyph_path"})
        return {r["id"]: r["glyph_path"] for r in rows}

    async def collective(self, entity_ids: list[str]) -> list[dict]:
        if not entity_ids:
            return []
        res = await self.sb._do("POST", "/rest/v1/rpc/symbol_emotions", self.sb.key, json_body={"p_entities": entity_ids})
        if res.status_code != 200:
            raise RuntimeError(f"lexicon: collective status {res.status_code}")
        return res.json()


class MemoryLexicon:
    """The same from lists, for DREAMLIB_DEV_AUTH=1 and the tests."""

    def __init__(self, aliases: dict[str, str] | None = None, entries: list[dict] | None = None, totals: list[dict] | None = None,
                 icons: dict[str, str] | None = None):
        self.known, self.entries, self.totals, self.icons = aliases or {}, entries or [], totals or [], icons or {}
        self.counts: dict[tuple[str, str], int] = {}

    async def glyphs(self, entity_ids: list[str]) -> dict[str, str]:
        return {i: self.icons[i] for i in entity_ids if self.icons.get(i)}

    async def symbol(self, entity_id: str) -> dict | None:
        names = [a for a, i in self.known.items() if i == entity_id]
        return {"id": entity_id, "labels": {"tr": names[0]}, "glyph_path": self.icons.get(entity_id, "")} if names else None

    async def seen(self, user_id: str, entity_id: str) -> int:
        return self.counts.get((user_id, entity_id), 0)

    async def aliases(self) -> dict[str, str]:
        return dict(self.known)

    async def meanings(self, entity_ids: list[str], per_symbol: int = 2) -> list[dict]:
        out, count = [], {}
        for r in self.entries:
            if r["entity_id"] in entity_ids and count.get(r["entity_id"], 0) < per_symbol:
                count[r["entity_id"]] = count.get(r["entity_id"], 0) + 1
                out.append(r)
        return out

    async def collective(self, entity_ids: list[str]) -> list[dict]:
        return [t for t in self.totals if t["entity_id"] in entity_ids]
