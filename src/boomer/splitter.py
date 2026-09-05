from copy import deepcopy
import logging
from boomer.model import (
    KB,
    Fact,
    EntityIdentifier,
    SubClassOf,
    ProperSubClassOf,
    EquivalentTo,
)
from typing import Iterator, Set
import networkx as nx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def fact_entities(fact: Fact) -> Set[EntityIdentifier]:
    """
    Return the entity identifiers mentioned by a fact.

    Introspects the fact's fields rather than assuming property names, so it
    works for every fact type. Tuple-valued fields (DisjointSet) and nested
    facts (NegatedFact) are flattened; a disjoint group name is not an entity.

    >>> sorted(fact_entities(SubClassOf(sub="a", sup="b")))
    ['a', 'b']
    >>> from boomer.model import DisjointSet, NegatedFact
    >>> sorted(fact_entities(DisjointSet(entities=("a", "b", "c"))))
    ['a', 'b', 'c']
    >>> sorted(fact_entities(NegatedFact(negated=SubClassOf(sub="a", sup="b"))))
    ['a', 'b']
    >>> from boomer.model import MemberOfDisjointGroup
    >>> sorted(fact_entities(MemberOfDisjointGroup(sub="a", group="ONT")))
    ['a']
    """
    entities: Set[EntityIdentifier] = set()
    for name, value in fact.__dict__.items():
        if name in ("fact_type", "group"):
            continue
        if isinstance(value, str):
            entities.add(value)
        elif isinstance(value, (tuple, list)):
            entities.update(value)
        elif isinstance(value, BaseModel):
            entities.update(fact_entities(value))
    return entities

def pfact_owner_entity(fact: Fact) -> EntityIdentifier:
    """
    The entity whose component owns a pfact when a KB is partitioned.

    Subclass-type facts belong with their subclass; symmetric facts have both
    ends in one strongly connected component anyway; anything else goes with
    its alphabetically first entity.

    >>> pfact_owner_entity(SubClassOf(sub="b", sup="a"))
    'b'
    >>> from boomer.model import DisjointWith
    >>> pfact_owner_entity(DisjointWith(sub="b", sibling="a"))
    'a'
    """
    if isinstance(fact, (SubClassOf, ProperSubClassOf, EquivalentTo)):
        return fact.sub
    return min(fact_entities(fact))


def kb_entities(kb: KB) -> Set[EntityIdentifier]:
    """All entities mentioned by a KB's facts and pfacts."""
    entities: Set[EntityIdentifier] = set()
    for fact in kb.facts:
        entities |= fact_entities(fact)
    for pfact in kb.pfacts:
        entities |= fact_entities(pfact.fact)
    return entities


def kb_to_graph(kb: KB) -> nx.DiGraph:
    """
    Create a graph of entities from both facts and pfacts.

    This function creates a directed graph where each node represents an entity, and each edge represents a relationship between two entities.
    The graph is used to identify strongly connected components of the entities.
    Every entity mentioned by any fact or pfact is a node, so entities that only
    appear in e.g. DisjointWith facts still land in a (singleton) component.

    Args:
        kb: Knowledge base to convert to graph

    Returns:
        A directed graph of entities
    """
    graph = nx.DiGraph()
    graph.add_nodes_from(kb_entities(kb))

    def add_edges(fact: Fact, edge_properties: dict = None):
        if not edge_properties:
            edge_properties = {}
        if isinstance(fact, EquivalentTo):
            graph.add_edge(fact.sub, fact.equivalent, **edge_properties)
            graph.add_edge(fact.equivalent, fact.sub, **edge_properties)
        elif isinstance(fact, SubClassOf):
            graph.add_edge(fact.sub, fact.sup, **edge_properties)
        elif isinstance(fact, ProperSubClassOf):
            graph.add_edge(fact.sub, fact.sup, **edge_properties)

    # Add edges from deterministic facts
    for fact in kb.facts:
        add_edges(fact)

    # Add edges from probabilistic facts
    for pfact in kb.pfacts:
        add_edges(pfact.fact, edge_properties={"prob": pfact.prob})

    return graph

def extract_sub_kb(
    kb: KB,
    component: Set[EntityIdentifier],
    include_labels: bool = True,
    own_pfacts: bool = False,
) -> KB:
    """
    Extract a sub-KB from a KB based on a set of entities.

    Args:
        kb: Knowledge base to extract sub-KB from
        component: Set of entities to extract
        include_labels: Whether to copy labels for the component's entities
        own_pfacts: If False, every pfact touching the component is included,
            so a pfact spanning two components is copied into both. If True,
            a pfact is included only in the component of its owner entity
            (see pfact_owner_entity), so each pfact lands in exactly one
            sub-KB; hard facts touching any entity of those pfacts are
            included as well, so the far end of a spanning pfact keeps its
            constraints.

    Returns:
        A sub-KB containing only the entities in the component
    """
    if own_pfacts:
        component_pfacts = [
            pfact for pfact in kb.pfacts if pfact_owner_entity(pfact.fact) in component
        ]
        fact_scope = set(component)
        for pfact in component_pfacts:
            fact_scope |= fact_entities(pfact.fact)
    else:
        component_pfacts = [pfact for pfact in kb.pfacts if fact_entities(pfact.fact) & component]
        fact_scope = component
    component_facts = [fact for fact in kb.facts if fact_entities(fact) & fact_scope]
    labels = {}
    if include_labels:
        labels = {entity: label for entity, label in kb.labels.items() if entity in fact_scope}
    sub_kb = KB(
            facts=component_facts,
            pfacts=component_pfacts,
            hypotheses=[hyp for hyp in kb.hypotheses if fact_entities(hyp) & component]
            if kb.hypotheses
            else [],
            name=kb.name,
            description=kb.description,
            comments=kb.comments,
            labels=labels,
            hyperparams=list(kb.hyperparams),
            pfacts_entailed=[pf for pf in kb.pfacts_entailed if fact_entities(pf.fact) & component],
            default_configurations=kb.default_configurations,
        )
    return sub_kb

def extract_neighborhood(
    kb: KB,
    seeds: set[EntityIdentifier],
    max_hops: int | None = None,
) -> KB:
    """Extract a sub-KB containing *seeds* and all transitively connected entities.

    Builds an undirected view of the entity graph (from both facts and pfacts)
    and finds every entity reachable from any seed.  An optional *max_hops*
    parameter limits the BFS depth.

    After the reachable entity set is determined, ``extract_sub_kb`` is used
    to collect all facts, pfacts, and labels that touch those entities.

    >>> from boomer.model import KB, PFact, EquivalentTo, SubClassOf
    >>> kb = KB(
    ...     pfacts=[
    ...         PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
    ...         PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
    ...         PFact(fact=EquivalentTo(sub="D", equivalent="E"), prob=0.7),
    ...     ],
    ...     labels={"A": "alpha", "B": "beta", "C": "gamma", "D": "delta", "E": "epsilon"},
    ... )
    >>> sub = extract_neighborhood(kb, {"A"})
    >>> sorted(sub.labels)
    ['A', 'B', 'C']
    >>> len(sub.pfacts)
    2

    >>> sub2 = extract_neighborhood(kb, {"A"}, max_hops=1)
    >>> sorted(sub2.labels)
    ['A', 'B']
    """
    graph = kb_to_graph(kb)
    undirected = graph.to_undirected()

    reachable: set[EntityIdentifier] = set()
    if max_hops is None:
        # Full transitive closure — collect entire connected component(s)
        for seed in seeds:
            if seed in undirected:
                reachable |= nx.node_connected_component(undirected, seed)
            else:
                reachable.add(seed)
    else:
        # BFS with hop limit
        for seed in seeds:
            if seed not in undirected:
                reachable.add(seed)
                continue
            lengths = nx.single_source_shortest_path_length(undirected, seed, cutoff=max_hops)
            reachable |= set(lengths)

    return extract_sub_kb(kb, reachable, include_labels=True)


def add_carried_facts(sub_kb: KB, kb: KB, carried: list[Fact]) -> KB:
    """
    Return *sub_kb* extended with facts accepted by previously solved sub-KBs.

    Carried facts that touch an entity of *sub_kb*, or an entity of another
    carried fact already pulled in, are added transitively, together with the
    hard facts of *kb* that touch any of those entities, so the constraints
    behind an earlier decision travel with it. The input is not modified.

    >>> from boomer.model import PFact, NotInSubsumptionWith
    >>> kb = KB(
    ...     facts=[NotInSubsumptionWith(sub="A", sibling="C")],
    ...     pfacts=[PFact(fact=SubClassOf(sub="A", sup="B"), prob=0.9),
    ...             PFact(fact=SubClassOf(sub="B", sup="C"), prob=0.9)],
    ... )
    >>> sub = KB(pfacts=[PFact(fact=SubClassOf(sub="B", sup="C"), prob=0.9)])
    >>> extended = add_carried_facts(sub, kb, [SubClassOf(sub="A", sup="B")])
    >>> extended.facts
    [SubClassOf(fact_type='SubClassOf', sub='A', sup='B'), NotInSubsumptionWith(fact_type='NotInSubsumptionWith', sub='A', sibling='C')]
    >>> sub.facts
    []
    """
    scope = kb_entities(sub_kb)
    relevant: list[Fact] = []
    pending = list(carried)
    grew = True
    while grew:
        grew = False
        for fact in list(pending):
            if fact_entities(fact) & scope:
                relevant.append(fact)
                pending.remove(fact)
                scope |= fact_entities(fact)
                grew = True
    if not relevant:
        return sub_kb
    present = set(sub_kb.facts) | set(relevant)
    context = [fact for fact in kb.facts if fact_entities(fact) & scope and fact not in present]
    return sub_kb.model_copy(update={"facts": sub_kb.facts + relevant + context})


def partition_kb(kb: KB, max_pfacts_per_clique: int | None = None, min_pfacts_per_clique: int = 5) -> Iterator[KB]:
    """
    Partition a KB into sub-KBs based on strongly connected components of the entity graph.

    This function identifies ontological cliques - groups of entities that are mutually reachable
    through directed relationships. EquivalentTo creates bidirectional edges, while SubClassOf
    and ProperSubClassOf create unidirectional edges. Only entities that can reach each other
    through these directed paths are grouped together.

    Each pfact is assigned to exactly one sub-KB, the one owning its
    pfact_owner_entity; a one-directional pfact whose ends fall in different
    components goes with its subclass end and its far end's hard facts come
    along. Hard facts are copied into every sub-KB they touch.

    Args:
        kb: Knowledge base to partition
        max_pfacts_per_clique: Optional limit on pfacts per clique. If a clique exceeds this,
            it is split further by temporarily dropping low-probability pfacts (see
            split_connected_components).

    For larger cliques with multiple equivalent entities:
    - A clique of 3 equivalent entities (A≡B≡C) forms one strongly connected component
    - Mixed relationships create larger components: if A⊆B, B≡C, C⊆D, D≡A, then {A,B,C,D}
      forms one component since all entities are mutually reachable
    - Isolated entities with only outgoing edges (e.g., A⊆B with no reverse path) remain separate
    - When max_pfacts_per_clique is set, large cliques are pruned to keep only the most probable facts

    >>> from boomer.model import KB, SubClassOf, DisjointWith, PFact, EquivalentTo
    >>> facts = [
    ...     SubClassOf(sub="cat", sup="animal"),
    ...     SubClassOf(sub="dog", sup="animal"),
    ...     DisjointWith(sub="red", sibling="blue")
    ... ]
    >>> pfacts = [
    ...     PFact(fact=EquivalentTo(sub="cat", equivalent="feline"), prob=0.9),
    ...     PFact(fact=EquivalentTo(sub="red", equivalent="crimson"), prob=0.8)
    ... ]
    >>> kb = KB(facts=facts, pfacts=pfacts)
    >>> partitions = list(partition_kb(kb))
    >>> len(partitions)  # {cat, feline}, {animal}, {dog}, {red, crimson}, {blue}
    5
    >>> sum(len(p.pfacts) for p in partitions)
    2

    >>> # Example with larger clique - three equivalent entities
    >>> kb_clique = KB(pfacts=[
    ...     PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
    ...     PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.9),
    ...     PFact(fact=EquivalentTo(sub="A", equivalent="C"), prob=0.9)
    ... ])
    >>> clique_partitions = list(partition_kb(kb_clique))
    >>> len(clique_partitions)
    1
    >>> len(clique_partitions[0].pfacts)
    3

    >>> # Example with clique size limit - keeps only highest probability pfacts
    >>> kb_large = KB(pfacts=[
    ...     PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
    ...     PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
    ...     PFact(fact=EquivalentTo(sub="C", equivalent="D"), prob=0.7),
    ...     PFact(fact=EquivalentTo(sub="A", equivalent="C"), prob=0.6),
    ...     PFact(fact=EquivalentTo(sub="A", equivalent="D"), prob=0.5)
    ... ])
    >>> limited_partitions = list(partition_kb(kb_large, max_pfacts_per_clique=3))
    >>> len(limited_partitions[0].pfacts)
    3
    >>> # Should keep the 3 highest probability pfacts: 0.9, 0.8, 0.7
    >>> sorted([pf.prob for pf in limited_partitions[0].pfacts], reverse=True)
    [0.9, 0.8, 0.7]
    """
    # create a graph of entities from both facts and pfacts
    graph = kb_to_graph(kb)

    # Partition into connected components
    for component in nx.strongly_connected_components(graph):
        # pfacts owned by this component, plus the hard facts they touch
        sub_kb = extract_sub_kb(kb, component, include_labels=False, own_pfacts=True)
        component_pfacts = sub_kb.pfacts

        # Apply clique size limit if specified
        if (
            max_pfacts_per_clique is not None
            and len(component_pfacts) > max_pfacts_per_clique
        ):
            logger.info(f"Splitting {len(component_pfacts)} pfacts into {max_pfacts_per_clique} pfacts per clique")
            yield from split_connected_components(sub_kb, max_pfacts_per_clique=max_pfacts_per_clique, min_pfacts_per_clique=min_pfacts_per_clique)
        else:
            yield sub_kb
        
def split_connected_components(kb: KB, max_pfacts_per_clique: int, min_pfacts_per_clique: int = 5) -> Iterator[KB]:
    """
    Split a KB into sub-KBs based on strongly connected components of the entity graph.

    Low-probability pfacts are dropped in batches until the remaining graph
    falls apart into a component of acceptable size, which is yielded; the
    dropped pfacts then return to the pool. If even the smallest pool cannot
    be split (every component still exceeds the limit once the minimum size
    has been relaxed to zero), the remaining components are yielded as they
    are, oversized, with a warning. Each pfact is yielded exactly once.

    TODO: rewrite this to be more efficient

    Args:
        kb: Knowledge base to split
        max_pfacts_per_clique: Limit on pfacts per clique that a split must respect.
        min_pfacts_per_clique: Smallest component worth yielding; relaxed by one
            each time a full pass finds no split.
    """
    if min_pfacts_per_clique > max_pfacts_per_clique:
        min_pfacts_per_clique = max_pfacts_per_clique
    kb = deepcopy(kb)
    kb.pfacts.sort(key=lambda pf: pf.prob, reverse=True)
    logger.info(f"Initial pfacts: {len(kb.pfacts)}")
    n = 0
    while kb.pfacts:
        dropped_pfacts = []
        is_split = False
        # never drop more than a clique's worth at once, or the pool can skip
        # straight past every size that would fit
        step_size = max(1, min((len(kb.pfacts) // 20) + 1, max_pfacts_per_clique))
        # print(f"step_size: {step_size}")
        # print(f"n: {n} // {len(kb.pfacts)} // step={step_size} // min_pfacts_per_clique={min_pfacts_per_clique}")

        while not is_split and kb.pfacts:
            graph = kb_to_graph(kb)
            components = list(nx.strongly_connected_components(graph))
            # remove singletons, caused by 
            components.sort(key=lambda c: len(c), reverse=True)
            # print(f"  NUM COMPONENTS: {len(components)} // {components}")
            for component in components:
                if len(component) == 1 and min_pfacts_per_clique > 0:
                    # avoid singletons
                    continue
                component_kb = extract_sub_kb(kb, component, include_labels=False, own_pfacts=True)
                # a split must carry at least one pfact, or the pool never shrinks
                if max(min_pfacts_per_clique, 1) <= len(component_kb.pfacts) <= max_pfacts_per_clique:
                    logger.info(f"Found split: {len(component_kb.pfacts)} / {len(kb.pfacts)} pfacts; component={component}/ all={components}")
                    yield component_kb
                    kb.pfacts += dropped_pfacts
                    kb.pfacts = [pf for pf in kb.pfacts if pf not in component_kb.pfacts]
                    # keep the pool sorted so later drops are lowest-probability first
                    kb.pfacts.sort(key=lambda pf: pf.prob, reverse=True)
                    logger.info(f"Remaining: {len(kb.pfacts)} pfacts [re-adding {len(dropped_pfacts)} dropped]")
                    dropped_pfacts = []
                    is_split = True
                    n += 1
                    break
            if not is_split:
                # keep dropping the lowest probability pfact until we find a suitable split
                # TODO: consider dropping more than one pfact at a time?
                last_pfacts = kb.pfacts[-step_size:]
                logger.info(f"Dropping pfacts: {last_pfacts}")
                kb.pfacts = kb.pfacts[:-step_size]
                dropped_pfacts.extend(last_pfacts)
        if dropped_pfacts:
            kb.pfacts += dropped_pfacts
            kb.pfacts.sort(key=lambda pf: pf.prob, reverse=True)
            logger.info(f"Re-adding {len(dropped_pfacts)} dropped pfacts")
            if min_pfacts_per_clique <= 0:
                # every relaxation has been tried; give up on splitting the rest
                break
            min_pfacts_per_clique -= 1
    if kb.pfacts:
        logger.warning(
            f"No split found for {len(kb.pfacts)} pfacts; yielding their components as they are, "
            f"which may exceed max_pfacts_per_clique={max_pfacts_per_clique}"
        )
        graph = kb_to_graph(kb)
        for component in nx.strongly_connected_components(graph):
            component_kb = extract_sub_kb(kb, component, include_labels=False, own_pfacts=True)
            if component_kb.pfacts:
                yield component_kb
                
        
        
        
