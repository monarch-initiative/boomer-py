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

logger = logging.getLogger(__name__)


def fact_entities(fact: Fact) -> Set[EntityIdentifier]:
    # introspect the fact to get the entities; don't assume properties
    entities = set()
    for k, v in fact.__dict__.items():
        entities.add(v)
    return entities

def kb_to_graph(kb: KB) -> nx.DiGraph:
    """
    Create a graph of entities from both facts and pfacts.

    This function creates a directed graph where each node represents an entity, and each edge represents a relationship between two entities.
    The graph is used to identify strongly connected components of the entities.

    Args:
        kb: Knowledge base to convert to graph

    Returns:
        A directed graph of entities
    """
    graph = nx.DiGraph()

    def add_edges(fact: Fact, edge_properties: dict = None):
        if not edge_properties:
            edge_properties = {}
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

def extract_sub_kb(kb: KB, component: Set[EntityIdentifier], include_labels: bool = True) -> KB:
    """
    Extract a sub-KB from a KB based on a set of entities.

    Args:
        kb: Knowledge base to extract sub-KB from
        component: Set of entities to extract

    Returns:
        A sub-KB containing only the entities in the component
    """
    component_facts = [fact for fact in kb.facts if fact_entities(fact) & component]
    component_pfacts = [pfact for pfact in kb.pfacts if fact_entities(pfact.fact) & component]
    labels = {}
    if include_labels:
        labels = {entity: label for entity, label in kb.labels.items() if entity in component}
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


def partition_kb(kb: KB, max_pfacts_per_clique: int | None = None, min_pfacts_per_clique: int = 5) -> Iterator[KB]:
    """
    Partition a KB into sub-KBs based on strongly connected components of the entity graph.

    This function identifies ontological cliques - groups of entities that are mutually reachable
    through directed relationships. EquivalentTo creates bidirectional edges, while SubClassOf
    and ProperSubClassOf create unidirectional edges. Only entities that can reach each other
    through these directed paths are grouped together.

    Args:
        kb: Knowledge base to partition
        max_pfacts_per_clique: Optional limit on pfacts per clique. If a clique exceeds this,
            only the highest probability pfacts are kept to manage computational complexity.

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
    >>> len(partitions)
    4

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
        # Include facts and pfacts that share entities with this component
        sub_kb = extract_sub_kb(kb, component, include_labels=False)
        component_pfacts = sub_kb.pfacts

        # Apply clique size limit if specified
        if (
            max_pfacts_per_clique is not None
            and len(component_pfacts) > max_pfacts_per_clique
        ):
            logger.info(f"Splitting {len(component_pfacts)} pfacts into {max_pfacts_per_clique} pfacts per clique")
            yield from split_connected_components(sub_kb, max_pfacts_per_clique=max_pfacts_per_clique, min_pfacts_per_clique=min_pfacts_per_clique)
            if False:
                # Sort by probability (descending) and keep only the highest probability pfacts
                component_pfacts.sort(key=lambda pf: pf.prob, reverse=True)
                # TODO: weave these back in; see diagonal test
                number_to_drop = int((len(component_pfacts) - max_pfacts_per_clique) / 10) + 1
                sub_kb.pfacts = component_pfacts[:-number_to_drop]
                yield from partition_kb(sub_kb, max_pfacts_per_clique=max_pfacts_per_clique)
        else:
            yield sub_kb
        
def split_connected_components(kb: KB, max_pfacts_per_clique: int, min_pfacts_per_clique: int = 5) -> Iterator[KB]:
    """
    Split a KB into sub-KBs based on strongly connected components of the entity graph.

    TODO: rewrite this to be more efficient

    Args:
        kb: Knowledge base to split
        max_pfacts_per_clique: Optional limit on pfacts per clique. If a clique exceeds this,
            only the highest probability pfacts are kept to manage computational complexity.
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
        step_size = (len(kb.pfacts) // 20) + 1
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
                component_kb = extract_sub_kb(kb, component, include_labels=False)
                #if len(components) > 1:
                #    component_kb = extract_sub_kb(kb, component)
                #else:
                #    component_kb = kb
                if len(component_kb.pfacts) <= max_pfacts_per_clique and len(component_kb.pfacts) >= min_pfacts_per_clique:
                    logger.info(f"Found split: {len(component_kb.pfacts)} / {len(kb.pfacts)} pfacts; component={component}/ all={components}")
                    yield component_kb
                    kb.pfacts += dropped_pfacts
                    kb.pfacts = [pf for pf in kb.pfacts if pf not in component_kb.pfacts]
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
            min_pfacts_per_clique -= 1
            logger.info(f"Re-adding {len(dropped_pfacts)} dropped pfacts")
    if kb.pfacts:
        logger.info(f"No split found; remaining: {len(kb.pfacts)} pfacts")
        graph = kb_to_graph(kb)
        components = list(nx.strongly_connected_components(graph))
        for component in components:
            component_kb = extract_sub_kb(kb, component, include_labels=True)
            yield component_kb
                
        
        
        
