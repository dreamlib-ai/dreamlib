"""BG1: how one dream relates to the dreamer's other dreams, without a model (docs/motor.md, docs/gorevler.md).

Four relation types, each its own coloured link in the brain graph:
- shares_content: symbols, characters, places, actions in common;
- shares_concept: themes (genre, experience) in common;
- shares_emotion: the same stated emotions;
- near_in_time: dreamt a few days apart.
The shared-node types weigh each node by how rare it is among this person's dreams (IDF), as a weighted
Jaccard: sum of shared weights over the union's. A link below its type's threshold is not kept, and each
dream keeps at most `TOP` links per type, so a new dream that barely touches the others floats free."""
import math
from dataclasses import dataclass, field
from datetime import date

VERSION = 1
FAMILIES = {  # entity kind -> relation
    "symbol": "shares_content", "character": "shares_content", "place": "shares_content", "action": "shares_content",
    "setting": "shares_content", "interaction": "shares_content", "outcome": "shares_content",
    "theme": "shares_concept", "archetype": "shares_concept", "motif": "shares_concept",
    "emotion": "shares_emotion",
}
THRESHOLD = {"shares_content": 0.2, "shares_concept": 0.34, "shares_emotion": 0.5, "near_in_time": 0.5}
RELATIONS = tuple(THRESHOLD)
TOP = {"shares_content": 6, "shares_concept": 6, "shares_emotion": 4, "near_in_time": 3}
HALF_LIFE_DAYS = 3.0
EVIDENCE = 8  # shared nodes kept as evidence per link


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    key: str
    label: str


@dataclass
class DreamNodes:
    id: str
    dated: date
    nodes: dict[str, Node] = field(default_factory=dict)  # entity id -> node


@dataclass(frozen=True)
class Edge:
    relation: str
    source: str  # sorts before target (symmetric relations are stored once)
    target: str
    weight: float
    evidence: dict


def _idf(corpus: list[DreamNodes]) -> dict[str, float]:
    df: dict[str, int] = {}
    for d in corpus:
        for eid in d.nodes:
            df[eid] = df.get(eid, 0) + 1
    n = len(corpus)
    return {eid: math.log(1 + n / count) for eid, count in df.items()}


def _shared(a: DreamNodes, b: DreamNodes, relation: str, idf: dict[str, float]) -> tuple[float, list[Node]]:
    mine = {e for e, n in a.nodes.items() if FAMILIES.get(n.kind) == relation}
    theirs = {e for e, n in b.nodes.items() if FAMILIES.get(n.kind) == relation}
    common = mine & theirs
    if not common:
        return 0.0, []
    union = sum(idf[e] for e in mine | theirs)
    weight = sum(idf[e] for e in common) / union if union else 0.0
    nodes = sorted((a.nodes[e] for e in common), key=lambda n: -idf[n.id])
    return weight, nodes


def relate(dream_id: str, corpus: list[DreamNodes]) -> list[Edge]:
    """The links of one dream to the others in its owner's corpus, strongest first within each type."""
    me = next((d for d in corpus if d.id == dream_id), None)
    if me is None:
        return []
    idf = _idf(corpus)
    found: dict[str, list[Edge]] = {r: [] for r in RELATIONS}
    for other in corpus:
        if other.id == me.id:
            continue
        a, b = sorted((me.id, other.id))
        for relation in ("shares_content", "shares_concept", "shares_emotion"):
            weight, nodes = _shared(me, other, relation, idf)
            if weight >= THRESHOLD[relation]:
                evidence = {"shared": [{"kind": n.kind, "key": n.key, "label": n.label} for n in nodes[:EVIDENCE]]}
                found[relation].append(Edge(relation, a, b, round(weight, 4), evidence))
        days = abs((me.dated - other.dated).days)
        weight = 0.5 ** (days / HALF_LIFE_DAYS)
        if weight >= THRESHOLD["near_in_time"]:
            found["near_in_time"].append(Edge("near_in_time", a, b, round(weight, 4), {"days": days}))
    out: list[Edge] = []
    for relation, edges in found.items():
        out += sorted(edges, key=lambda e: -e.weight)[:TOP[relation]]
    return out
