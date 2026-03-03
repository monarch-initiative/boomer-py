"""
OBOGraphs JSON solution renderer for boomer.

Renders a boomer Solution as an OBOGraphs JSON document — the standard
graph exchange format used by OAK, Monarch, and the broader OBO community.

See https://github.com/geneontology/obographs for the specification.
"""

import json
from dataclasses import dataclass
from typing import Any, Optional

from boomer.model import (
    DisjointWith,
    EquivalentTo,
    Fact,
    KB,
    ProperSubClassOf,
    Solution,
    SubClassOf,
)
from boomer.renderers.renderer import Renderer

# ---------------------------------------------------------------------------
# Fact type → OBOGraphs predicate
# ---------------------------------------------------------------------------

FACT_PRED_MAP: dict[str, str] = {
    "EquivalentTo": "owl:equivalentClass",
    "ProperSubClassOf": "is_a",
    "SubClassOf": "is_a",
    "DisjointWith": "owl:disjointWith",
}

# Fact types we silently skip (not representable in OBOGraphs edges)
_SKIP_TYPES = {"MemberOfDisjointGroup", "NegatedFact", "DisjointSet"}


def _make_node(entity_id: str, label: str | None = None) -> dict[str, str]:
    """Create an OBOGraphs node dict.

    >>> _make_node("GO:0001234", "some process")
    {'id': 'GO:0001234', 'lbl': 'some process'}

    >>> _make_node("CL:0000001")
    {'id': 'CL:0000001'}
    """
    node: dict[str, str] = {"id": entity_id}
    if label:
        node["lbl"] = label
    return node


def _extract_edge_entities(fact: Fact) -> tuple[str, str] | None:
    """Return ``(subject, object)`` entity IDs for a fact, or None if skipped."""
    if isinstance(fact, EquivalentTo):
        return (fact.sub, fact.equivalent)
    elif isinstance(fact, (ProperSubClassOf, SubClassOf)):
        return (fact.sub, fact.sup)
    elif isinstance(fact, DisjointWith):
        return (fact.sub, fact.sibling)
    return None


def _fact_to_edge(fact: Fact, meta: dict | None = None) -> dict[str, Any] | None:
    """Convert a boomer Fact to an OBOGraphs edge dict, or None if not representable.

    >>> from boomer.model import EquivalentTo
    >>> _fact_to_edge(EquivalentTo(sub="A:1", equivalent="B:2"))
    {'sub': 'A:1', 'pred': 'owl:equivalentClass', 'obj': 'B:2'}

    >>> from boomer.model import ProperSubClassOf
    >>> _fact_to_edge(ProperSubClassOf(sub="X:1", sup="Y:2"))
    {'sub': 'X:1', 'pred': 'is_a', 'obj': 'Y:2'}

    >>> from boomer.model import MemberOfDisjointGroup
    >>> _fact_to_edge(MemberOfDisjointGroup(sub="A:1", group="g")) is None
    True
    """
    fact_type = fact.__class__.__name__
    pred = FACT_PRED_MAP.get(fact_type)
    if pred is None:
        return None

    entities = _extract_edge_entities(fact)
    if entities is None:
        return None

    edge: dict[str, Any] = {"sub": entities[0], "pred": pred, "obj": entities[1]}
    if meta:
        edge["meta"] = meta
    return edge


def solution_to_obograph(
    solution: Solution,
    kb: KB | None = None,
    include_hard_facts: bool = True,
    include_rejected: bool = False,
) -> dict[str, Any]:
    """Convert a Solution (and optional KB) to an OBOGraphs JSON-compatible dict.

    Parameters
    ----------
    solution:
        The solved solution from boomer.
    kb:
        Optional knowledge base (used for labels and hard facts).
    include_hard_facts:
        If True, include hard facts from ``kb.facts`` as edges.
    include_rejected:
        If True, include pfacts with ``truth_value=False``.

    Returns
    -------
    dict
        An OBOGraphs-compatible dict with a single graph under ``"graphs"``.
    """
    labels: dict[str, str] = kb.labels if kb else {}
    entity_ids: set[str] = set()
    edges: list[dict[str, Any]] = []

    # --- probabilistic facts ---
    for spf in solution.solved_pfacts:
        if not include_rejected and not spf.truth_value:
            continue

        fact = spf.pfact.fact
        edge_meta = {
            "basicPropertyValues": [
                {"pred": "boomer:posteriorProbability", "val": str(spf.posterior_prob)},
                {"pred": "boomer:priorProbability", "val": str(spf.pfact.prob)},
            ],
        }
        edge = _fact_to_edge(fact, meta=edge_meta)
        if edge is not None:
            edges.append(edge)
            entity_ids.add(edge["sub"])
            entity_ids.add(edge["obj"])

    # --- hard facts from KB ---
    if include_hard_facts and kb:
        for fact in kb.facts:
            edge = _fact_to_edge(fact)
            if edge is not None:
                edges.append(edge)
                entity_ids.add(edge["sub"])
                entity_ids.add(edge["obj"])

    # --- nodes ---
    nodes = [_make_node(eid, labels.get(eid)) for eid in sorted(entity_ids)]

    # --- graph-level metadata ---
    graph_meta: dict[str, Any] = {
        "basicPropertyValues": [
            {"pred": "boomer:confidence", "val": str(solution.confidence)},
            {"pred": "boomer:combinations", "val": str(solution.number_of_combinations)},
        ],
    }

    return {
        "graphs": [
            {
                "id": "boomer:solution",
                "meta": graph_meta,
                "nodes": nodes,
                "edges": edges,
            }
        ]
    }


@dataclass
class OBOGraphsRenderer(Renderer):
    """Render a boomer Solution as OBOGraphs JSON.

    Parameters
    ----------
    include_hard_facts : bool
        Include hard facts from ``kb.facts`` as edges (default True).
    include_rejected : bool
        Include rejected pfacts in the output (default False).
    """

    include_hard_facts: bool = True
    include_rejected: bool = False

    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:  # noqa: D102
        graph = solution_to_obograph(
            solution,
            kb,
            include_hard_facts=self.include_hard_facts,
            include_rejected=self.include_rejected,
        )
        return json.dumps(graph, indent=2)
