from collections import defaultdict
import networkx as nx

from boomer.model import *
from boomer.reasoners.reasoner import Reasoner, ReasonerResult


def negate_entity(entity: EntityIdentifier) -> EntityIdentifier:
    if entity.startswith("!"):
        return entity[1:]
    else:
        return f"!{entity}"


def filter_unsats(fact_states: List[Tuple[bool, PFactIndex, Fact]]) -> List[Fact]:
    tv_ix = defaultdict(set)
    for tv, _ix, fact in fact_states:
        tv_ix[fact].add((tv))
    return [fact for fact, tvs in tv_ix.items() if len(tvs) == 2]

    return [fact for tv, ix in fact_states if not tv and ix is not None]


class NxReasoner(Reasoner):
    """
    Reasoner that uses a networkx graph to reason about the KB.
    """

    def reason(
        self,
        kb: KB,
        selections: List[Grounding] | None = None,
        #candidates: List[PFactIndex] | None = None,
        additional_hypotheses: List[Fact] | None = None,
    ) -> ReasonerResult:
        if selections is None:
            selections = []
        #if candidates is None:
        #    candidates = list(range(0, len(kb.pfacts)))
        g = nx.DiGraph()
        asserted_true_facts = [
            kb.pfacts[c[0]].fact for c in selections if c[1]
        ] + kb.facts
        asserted_true_facts_by_type = defaultdict(list)
        for fact in asserted_true_facts:
            asserted_true_facts_by_type[type(fact)].append(fact)
        # print(f"asserted_true_facts: {asserted_true_facts}")
        has_one_of = any(isinstance(fact, OneOf) for fact in asserted_true_facts)
        for fact in asserted_true_facts:
            if isinstance(fact, EquivalentTo):
                g.add_edge(fact.sub, fact.equivalent)
                g.add_edge(fact.equivalent, fact.sub)
                if has_one_of:
                    g.add_edge(negate_entity(fact.sub), negate_entity(fact.equivalent))
                    g.add_edge(negate_entity(fact.equivalent), negate_entity(fact.sub))
            if isinstance(fact, (SubClassOf, ProperSubClassOf)):
                g.add_edge(fact.sub, fact.sup)
                if has_one_of:
                    g.add_edge(negate_entity(fact.sup), negate_entity(fact.sub))
            if isinstance(fact, OneOf):
                g.add_edge(fact.sub, negate_entity(fact.sibling))
                g.add_edge(negate_entity(fact.sibling), fact.sub)
        # print(f"g: {g.nodes()} // {kb} // {selections}")
        # print(f"g: {g.edges()}")
        # get strongly connected components
        sccs = list(nx.strongly_connected_components(g))

        # print(f"sccs: {sccs}")
        def is_equiv(n1: str, n2: str) -> bool:
            for scc in sccs:
                if n1 in scc and n2 in scc:
                    return True
            return False

        def is_subclass(sub: str, sup: str) -> bool:
            if sub in g and sup in g:
                return nx.has_path(g, sub, sup)
            return False

        # unasserted hypotheses; test each one to see if it is provably true or false from the asserted facts.
        # note that the reasoner is deterministic, so we don't care about the actual probability
        # of the pfact, it's just a hypothesis
        facts_to_check = [(i, pfact.fact) for i, pfact in enumerate(kb.pfacts)] + [
            (None, f) for f in kb.facts
        ]
        if additional_hypotheses:
            facts_to_check += [(None, h) for h in additional_hypotheses]
        disjoint_groups = defaultdict(list)
        disjoint_groups_by_entity = defaultdict(list)
        disjoint_sets = []
        for _, fact in facts_to_check:
            if isinstance(fact, MemberOfDisjointGroup):
                disjoint_groups[fact.group].append(fact.sub)
                disjoint_groups_by_entity[fact.sub].append(fact.group)
            elif isinstance(fact, DisjointSet):
                disjoint_sets.append(fact.entities)
        checked_selections = [(tv, ix, kb.pfacts[ix].fact) for ix, tv in selections]
        for ix, fact in facts_to_check:

            def add_entailment(tv: bool):
                if isinstance(fact, NegatedFact):
                    checked_selections.append((not tv, ix, fact))
                else:
                    checked_selections.append((tv, ix, fact))

            atomic_fact = fact.negated if isinstance(fact, NegatedFact) else fact
            if isinstance(atomic_fact, EquivalentTo):
                if is_equiv(atomic_fact.sub, atomic_fact.equivalent):
                    add_entailment(True)
                psos = asserted_true_facts_by_type.get(ProperSubClassOf)
                if psos:
                    for pso in psos:
                        if not isinstance(pso, ProperSubClassOf):
                            raise AssertionError(
                                f"incorrect index for {pso} in {asserted_true_facts_by_type}"
                            )
                        if (
                            pso.sub == atomic_fact.sub
                            and pso.sup == atomic_fact.equivalent
                        ):
                            add_entailment(False)
                        elif (
                            pso.sub == atomic_fact.equivalent
                            and pso.sup == atomic_fact.sub
                        ):
                            add_entailment(False)
            if isinstance(atomic_fact, (SubClassOf,)):
                if is_subclass(atomic_fact.sub, atomic_fact.sup):
                    add_entailment(True)
                    # checked_selections.append((True, ix, fact))
            if isinstance(atomic_fact, ProperSubClassOf):
                if is_equiv(atomic_fact.sub, atomic_fact.sup):
                    # cannot hold by definition
                    add_entailment(False)
                # note the is_subclass() checks for subclass-or-equivalence (OWL-DL symbol: ⊆)
                # if this holds, AND we know that two classes are not equivalent, then we can
                # infer that the proper subclass relation holds
                if disjoint_groups:
                    sub_dgs = set(disjoint_groups_by_entity.get(atomic_fact.sub, []))
                    sup_dgs = set(disjoint_groups_by_entity.get(atomic_fact.sup, []))
                    if sub_dgs & sup_dgs:
                        if is_subclass(atomic_fact.sub, atomic_fact.sup):
                            add_entailment(True)
                    # checked_selections.append((False, ix, fact))
            if isinstance(atomic_fact, NotInSubsumptionWith):
                if is_subclass(atomic_fact.sub, atomic_fact.sibling) or is_subclass(
                    atomic_fact.sibling, atomic_fact.sub
                ):
                    add_entailment(False)
                    #  checked_selections.append((False, ix, fact))
            if isinstance(atomic_fact, (OneOf, DisjointWith)):
                if is_subclass(atomic_fact.sub, atomic_fact.sibling) or is_subclass(
                    atomic_fact.sibling, atomic_fact.sub
                ):
                    add_entailment(False)
                    # checked_selections.append((False, ix, fact))
                else:
                    # check for common descendants (confusingly, nx reverses the terminology)
                    common_descendants = set(nx.ancestors(g, atomic_fact.sub)) & set(
                        nx.ancestors(g, atomic_fact.sibling)
                    )
                    if common_descendants:
                        add_entailment(False)
                        # checked_selections.append((False, ix, fact))
            if isinstance(atomic_fact, MemberOfDisjointGroup):
                grp = atomic_fact.group
                for other_member in disjoint_groups[grp]:
                    if other_member == atomic_fact.sub:
                        continue
                    if is_equiv(atomic_fact.sub, other_member):
                        add_entailment(False)
                        # checked_selections.append((False, ix, fact))
            if isinstance(atomic_fact, DisjointSet):
                # Check all pairwise disjointness constraints in the set
                for i, entity1 in enumerate(atomic_fact.entities):
                    for j, entity2 in enumerate(atomic_fact.entities):
                        if i >= j:  # Skip self and already checked pairs
                            continue
                        if is_equiv(entity1, entity2):
                            add_entailment(False)
                        elif is_subclass(entity1, entity2) or is_subclass(
                            entity2, entity1
                        ):
                            add_entailment(False)
                        else:
                            # Check for common descendants (entities that are subclasses of both)
                            # Only check if both entities are in the graph
                            if entity1 in g and entity2 in g:
                                common_descendants = set(
                                    nx.ancestors(g, entity1)
                                ) & set(nx.ancestors(g, entity2))
                                if common_descendants:
                                    add_entailment(False)
        checked_selections = list(set(checked_selections))
        return ReasonerResult(
            unsatisfiable_facts=filter_unsats(
                checked_selections + [(True, None, f) for f in kb.facts]
            ),
            entailed_selections=[
                (ix, tv) for tv, ix, _ in checked_selections if ix is not None
            ],
            entailed_hypotheses=[
                (pfact, tv) for tv, ix, pfact in checked_selections if ix is None and isinstance(pfact, PFact)
            ],
        )
