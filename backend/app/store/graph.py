"""A person's dream graph for BG1/BG2: their dreams with dates and nodes (`brain_links`), and the dream ↔ dream
edges the relation scorers write (app/engine/relations.py). Edges carry user_id; every query filters on it."""
from datetime import date, datetime

from ..engine.relations import RELATIONS, DreamNodes, Edge, Node
from .supabase import Supabase


def _corpus(rows: list[dict]) -> list[DreamNodes]:
    dreams: dict[str, DreamNodes] = {}
    for r in rows:
        d = dreams.setdefault(r["dream_id"], DreamNodes(r["dream_id"], date.fromisoformat(str(r["dated"])[:10])))
        if r.get("entity_id"):
            d.nodes[r["entity_id"]] = Node(r["entity_id"], r["kind"], r["key"], r["label"] or r["key"])
    return list(dreams.values())


class SupabaseGraph:
    def __init__(self, sb: Supabase):
        self.sb = sb

    async def _req(self, method: str, path: str, **kw):
        res = await self.sb._do(method, path, self.sb.key, **kw)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"graph: {method} {path} status {res.status_code}: {res.text.strip()[:300]}")
        return res

    async def corpus(self, user_id: str) -> list[DreamNodes]:
        res = await self._req("POST", "/rest/v1/rpc/brain_links", json_body={"p_user": user_id})
        return _corpus(res.json())

    async def replace(self, user_id: str, dream_id: str, edges: list[Edge]) -> None:
        """Drops this dream's scored links (either end) and writes the new ones."""
        await self._req("DELETE", "/rest/v1/edges", params={
            "user_id": f"eq.{user_id}", "relation": f"in.({','.join(RELATIONS)})",
            "or": f"(source_id.eq.{dream_id},target_id.eq.{dream_id})"})
        if edges:
            rows = [{"relation": e.relation, "source_id": e.source, "target_id": e.target, "user_id": user_id,
                     "weight": e.weight, "evidence": e.evidence} for e in edges]
            await self._req("POST", "/rest/v1/edges", json_body=rows, prefer="return=minimal")

    async def edges(self, user_id: str) -> list[dict]:
        params = {"user_id": f"eq.{user_id}", "relation": f"in.({','.join(RELATIONS)})",
                  "select": "relation,source_id,target_id,weight,evidence", "order": "weight.desc", "limit": "5000"}
        return (await self._req("GET", "/rest/v1/edges", params=params)).json()


class MemoryGraph:
    """The same over the in-memory dream store and entity links, for DREAMLIB_DEV_AUTH=1 and the tests."""

    def __init__(self, store, entities):
        self.store, self.entities = store, entities
        self.rows: list[dict] = []

    async def corpus(self, user_id: str) -> list[DreamNodes]:
        nodes = {n["id"]: (kind, key, n["labels"]) for (kind, key), n in self.entities.nodes.items()}
        rows = []
        for d in self.store.dreams.get(user_id, []):
            dated = d.journal.dreamedOn or (d.createdAt or datetime.now()).date()
            links = [l for l in self.entities.links if l["dream_id"] == d.id and l["entity_id"] in nodes]
            if not links:
                rows.append({"dream_id": d.id, "dated": dated, "entity_id": None})
            for l in links:
                kind, key, labels = nodes[l["entity_id"]]
                rows.append({"dream_id": d.id, "dated": dated, "entity_id": l["entity_id"], "kind": kind, "key": key,
                             "label": labels.get("tr") or labels.get("en") or key})
        return _corpus(rows)

    async def replace(self, user_id: str, dream_id: str, edges: list[Edge]) -> None:
        self.rows = [r for r in self.rows if not (r["user_id"] == user_id and dream_id in (r["source_id"], r["target_id"]))]
        self.rows += [{"relation": e.relation, "source_id": e.source, "target_id": e.target, "user_id": user_id,
                       "weight": e.weight, "evidence": e.evidence} for e in edges]

    async def edges(self, user_id: str) -> list[dict]:
        return sorted(({k: v for k, v in r.items() if k != "user_id"} for r in self.rows if r["user_id"] == user_id),
                      key=lambda r: -r["weight"])
