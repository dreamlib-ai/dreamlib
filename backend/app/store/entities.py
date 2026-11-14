"""Nodes (`entities`) and a dream's links to them (`dream_entities`), as far as the index job needs them.

ensure() finds or opens a node by (kind, key); link() replaces one extractor's links of a dream, so indexing
the same dream again leaves no stale rows behind."""
import uuid
from dataclasses import dataclass

from .supabase import Supabase


@dataclass(frozen=True)
class Node:
    kind: str
    key: str  # canonical, language independent, e.g. hvdc.anger
    labels: dict  # {"tr": ..., "en": ...}


@dataclass(frozen=True)
class Link:
    entity_id: str
    weight: float  # 0..1
    quote: str  # word for word from the narrative


class SupabaseEntities:
    def __init__(self, sb: Supabase):
        self.sb = sb
        self.ids: dict[tuple[str, str], str] = {}  # (kind, key) -> id; nodes are never deleted, only merged

    async def _req(self, method: str, path: str, **kw):
        res = await self.sb._do(method, path, self.sb.key, **kw)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"entities: {method} {path} status {res.status_code}: {res.text.strip()[:300]}")
        return res

    async def ensure(self, nodes: list[Node], status: str = "approved") -> dict[str, str]:
        """key -> id for these nodes of one kind, opening the missing ones."""
        missing = [n for n in nodes if (n.kind, n.key) not in self.ids]
        for kind in {n.kind for n in missing}:
            want = [n for n in missing if n.kind == kind]
            keys = ",".join(n.key for n in want)
            params = {"kind": f"eq.{kind}", "key": f"in.({keys})", "select": "id,key"}
            found = {r["key"]: r["id"] for r in (await self._req("GET", "/rest/v1/entities", params=params)).json()}
            new = [{"kind": kind, "key": n.key, "labels": n.labels, "status": status} for n in want if n.key not in found]
            if new:
                await self._req("POST", "/rest/v1/entities", json_body=new, prefer="resolution=ignore-duplicates,return=minimal",
                                params={"on_conflict": "kind,key"})
                found = {r["key"]: r["id"] for r in (await self._req("GET", "/rest/v1/entities", params=params)).json()}
            for key, id_ in found.items():
                self.ids[(kind, key)] = id_
        return {n.key: self.ids[(n.kind, n.key)] for n in nodes if (n.kind, n.key) in self.ids}

    async def get(self, entity_id: str) -> dict | None:
        res = await self._req("GET", "/rest/v1/entities", params={"id": f"eq.{entity_id}",
                                                                    "select": "id,kind,key,labels,status,glyph_path,glyph_prompt"})
        rows = res.json()
        return rows[0] if rows else None

    async def without_glyph(self, ids: list[str], version: str) -> list[str]:
        """G1, G2: of these nodes, the approved symbols with no icon yet or one drawn with an older revision."""
        if not ids:
            return []
        res = await self._req("GET", "/rest/v1/entities", params={
            "id": f"in.({','.join(ids)})", "kind": "eq.symbol", "status": "eq.approved", "glyph_prompt": f"neq.{version}",
            "select": "id"})
        return [r["id"] for r in res.json()]

    async def set_glyph(self, entity_id: str, path: str, version: str) -> None:
        await self._req("PATCH", "/rest/v1/entities", params={"id": f"eq.{entity_id}"},
                        json_body={"glyph_path": path, "glyph_prompt": version}, prefer="return=minimal")

    async def link(self, dream_id: str, extractor: str, links: list[Link], source: str = "model") -> None:
        await self._req("DELETE", "/rest/v1/dream_entities",
                        params={"dream_id": f"eq.{dream_id}", "source": f"eq.{source}", "extractor": f"eq.{extractor}"})
        if links:
            rows = [{"dream_id": dream_id, "entity_id": l.entity_id, "weight": l.weight, "source": source,
                     "extractor": extractor, "quote": l.quote[:300]} for l in links]
            await self._req("POST", "/rest/v1/dream_entities", json_body=rows, prefer="return=minimal")


class MemoryEntities:
    """The same in dictionaries, for DREAMLIB_DEV_AUTH=1 and the tests."""

    def __init__(self):
        self.nodes: dict[tuple[str, str], dict] = {}
        self.links: list[dict] = []

    async def ensure(self, nodes: list[Node], status: str = "approved") -> dict[str, str]:
        out = {}
        for n in nodes:
            row = self.nodes.setdefault((n.kind, n.key), {"id": str(uuid.uuid4()), "labels": n.labels, "status": status,
                                                          "kind": n.kind, "key": n.key, "glyph_path": "", "glyph_prompt": ""})
            out[n.key] = row["id"]
        return out

    async def get(self, entity_id: str) -> dict | None:
        return next((dict(r) for r in self.nodes.values() if r["id"] == entity_id), None)

    async def without_glyph(self, ids: list[str], version: str) -> list[str]:
        return [r["id"] for r in self.nodes.values()
                if r["id"] in ids and r["kind"] == "symbol" and r["status"] == "approved" and r["glyph_prompt"] != version]

    async def set_glyph(self, entity_id: str, path: str, version: str) -> None:
        for r in self.nodes.values():
            if r["id"] == entity_id:
                r["glyph_path"], r["glyph_prompt"] = path, version

    async def link(self, dream_id: str, extractor: str, links: list[Link], source: str = "model") -> None:
        self.links = [l for l in self.links if not (l["dream_id"] == dream_id and l["extractor"] == extractor and l["source"] == source)]
        self.links += [{"dream_id": dream_id, "entity_id": l.entity_id, "weight": l.weight, "source": source,
                        "extractor": extractor, "quote": l.quote} for l in links]
