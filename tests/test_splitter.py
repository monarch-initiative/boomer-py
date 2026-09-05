import pytest
import boomer.datasets.diagonal as diagonal
from boomer.model import (
    KB,
    PFact,
    DisjointSet,
    DisjointWith,
    EquivalentTo,
    NegatedFact,
    NotInSubsumptionWith,
    ProperSubClassOf,
    MemberOfDisjointGroup,
    ProbabilityMissingProperSubClassOf,
    SearchConfig,
    SubClassOf,
)
from boomer.search import solve
from boomer.reasoners.nx_reasoner import NxReasoner
from boomer.splitter import (
    add_carried_facts,
    extract_neighborhood,
    extract_sub_kb,
    fact_entities,
    kb_to_graph,
    partition_kb,
    pfact_owner_entity,
    split_connected_components,
)


# ---------------------------------------------------------------------------
# extract_neighborhood tests
# ---------------------------------------------------------------------------

@pytest.fixture
def chain_kb() -> KB:
    """A -- B -- C    D -- E  (two disconnected components)."""
    return KB(
        pfacts=[
            PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
            PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
            PFact(fact=EquivalentTo(sub="D", equivalent="E"), prob=0.7),
        ],
        facts=[
            MemberOfDisjointGroup(sub="A", group="G1"),
            MemberOfDisjointGroup(sub="B", group="G1"),
            MemberOfDisjointGroup(sub="D", group="G2"),
        ],
        labels={"A": "alpha", "B": "beta", "C": "gamma", "D": "delta", "E": "epsilon"},
    )


def test_neighborhood_full_component(chain_kb):
    sub = extract_neighborhood(chain_kb, {"A"})
    assert sorted(sub.labels) == ["A", "B", "C"]
    assert len(sub.pfacts) == 2
    # Should include facts touching reachable entities
    assert any(f.sub == "A" for f in sub.facts)


def test_neighborhood_other_component(chain_kb):
    sub = extract_neighborhood(chain_kb, {"D"})
    assert sorted(sub.labels) == ["D", "E"]
    assert len(sub.pfacts) == 1


def test_neighborhood_max_hops_1(chain_kb):
    sub = extract_neighborhood(chain_kb, {"A"}, max_hops=1)
    assert sorted(sub.labels) == ["A", "B"]
    # B≡C pfact touches B (which is reachable), so it's included
    assert len(sub.pfacts) == 2


def test_neighborhood_max_hops_2(chain_kb):
    sub = extract_neighborhood(chain_kb, {"A"}, max_hops=2)
    assert sorted(sub.labels) == ["A", "B", "C"]
    assert len(sub.pfacts) == 2


def test_neighborhood_multiple_seeds(chain_kb):
    """Seeds from both components should merge."""
    sub = extract_neighborhood(chain_kb, {"A", "D"})
    assert sorted(sub.labels) == ["A", "B", "C", "D", "E"]
    assert len(sub.pfacts) == 3


def test_neighborhood_unknown_seed(chain_kb):
    """A seed not in the graph should still appear but pull nothing extra."""
    sub = extract_neighborhood(chain_kb, {"UNKNOWN:999"})
    assert len(sub.pfacts) == 0
    assert len(sub.labels) == 0


def test_neighborhood_subsumption_direction():
    """SubClassOf goes A->B; seeding from B should still reach A via undirected graph."""
    kb = KB(
        pfacts=[
            PFact(fact=ProperSubClassOf(sub="A", sup="B"), prob=0.9),
            PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
        ],
        labels={"A": "a", "B": "b", "C": "c"},
    )
    sub = extract_neighborhood(kb, {"C"})
    assert sorted(sub.labels) == ["A", "B", "C"]
    assert len(sub.pfacts) == 2


# ---------------------------------------------------------------------------
# split_connected_components tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("max_pfacts_per_clique,min_pfacts_per_clique", [(10, 5), (20, 10), (30, 15)])
def test_split_connected_components(max_pfacts_per_clique, min_pfacts_per_clique):
    kb = diagonal.create_kb()
    num_pfacts = len(kb.pfacts)
    pfacts = kb.pfacts
    kbs = list(split_connected_components(kb, max_pfacts_per_clique=max_pfacts_per_clique, min_pfacts_per_clique=min_pfacts_per_clique))
    print(len(kbs))
    total_pfacts = 0
    all_pfacts = []
    for sub_kb in kbs:
        print(f"sub-kb: {len(sub_kb.pfacts)}")
        total_pfacts += len(sub_kb.pfacts)
        for pfact in sub_kb.pfacts:
            if pfact not in all_pfacts:
                all_pfacts.append(pfact)
    for pfact in all_pfacts:
        if pfact not in pfacts:
            print(f"pfact {pfact} in combined sub-kbs but not in pfacts")
    for pfact in pfacts:
        if pfact not in all_pfacts:
            print(f"pfact {pfact} in pfacts but not in combined sub-kbs")
    #assert all_pfacts == pfacts
    assert total_pfacts == num_pfacts


# ---------------------------------------------------------------------------
# fact_entities / kb_to_graph / DisjointSet identity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fact,expected",
    [
        (SubClassOf(sub="a", sup="b"), {"a", "b"}),
        (DisjointSet(entities=("a", "b", "c")), {"a", "b", "c"}),
        (NegatedFact(negated=SubClassOf(sub="a", sup="b")), {"a", "b"}),
    ],
)
def test_fact_entities(fact, expected):
    assert fact_entities(fact) == expected


def test_partition_keeps_set_and_negated_facts():
    """DisjointSet and NegatedFact facts used to be dropped from every sub-KB."""
    disjoint = DisjointSet(entities=("a", "b", "c"))
    negated = NegatedFact(negated=SubClassOf(sub="a", sup="d"))
    kb = KB(
        facts=[disjoint, negated],
        pfacts=[PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.9)],
    )
    [sub_kb] = [s for s in partition_kb(kb) if s.pfacts]
    assert disjoint in sub_kb.facts
    assert negated in sub_kb.facts


@pytest.mark.parametrize("partition_initial_threshold", [200, 1])
def test_partition_respects_disjoint_set(partition_initial_threshold):
    kb = KB(
        facts=[DisjointSet(entities=("a", "b"))],
        pfacts=[PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.9)],
    )
    config = SearchConfig(partition_initial_threshold=partition_initial_threshold)
    solution = solve(kb, config)
    assert [sp.truth_value for sp in solution.solved_pfacts] == [False]


def test_kb_to_graph_keeps_pfact_probability():
    kb = KB(pfacts=[PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.8)])
    graph = kb_to_graph(kb)
    assert graph.edges["a", "b"]["prob"] == 0.8
    assert graph.edges["b", "a"]["prob"] == 0.8


def test_disjoint_set_entities_are_sorted():
    assert DisjointSet(entities=("b", "a")).entities == ("a", "b")
    assert DisjointSet(entities=["b", "a"]) == DisjointSet(entities=("a", "b"))
    assert hash(DisjointSet(entities=["b", "a"])) == hash(DisjointSet(entities=("a", "b")))


def test_extract_sub_kb_keeps_kb_level_settings():
    kb = KB(
        facts=[MemberOfDisjointGroup(sub="a", group="G"), MemberOfDisjointGroup(sub="b", group="G")],
        pfacts=[PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.5)],
        hyperparams=[
            ProbabilityMissingProperSubClassOf(prob=0.2, disjoint_group_sub="G", disjoint_group_sup="G")
        ],
        pfacts_entailed=[
            PFact(fact=ProperSubClassOf(sub="a", sup="b"), prob=0.2),
            PFact(fact=ProperSubClassOf(sub="c", sup="d"), prob=0.2),
        ],
        default_configurations={"default": SearchConfig(max_candidate_solutions=7)},
    )
    sub = extract_sub_kb(kb, {"a", "b"})
    assert sub.hyperparams == kb.hyperparams
    assert sub.pfacts_entailed == [kb.pfacts_entailed[0]]
    assert sub.default_configurations == kb.default_configurations


# ---------------------------------------------------------------------------
# pfact ownership, carry-forward, and bounded splitting
# ---------------------------------------------------------------------------


def _chain_kb():
    return KB(
        facts=[NotInSubsumptionWith(sub="A", sibling="C")],
        pfacts=[
            PFact(fact=SubClassOf(sub="A", sup="B"), prob=0.9),
            PFact(fact=SubClassOf(sub="B", sup="C"), prob=0.9),
        ],
    )


def test_partition_assigns_each_pfact_to_one_component():
    subs = [s for s in partition_kb(_chain_kb()) if s.pfacts]
    owners = [pf.fact for s in subs for pf in s.pfacts]
    assert sorted(owners, key=str) == sorted([pf.fact for pf in _chain_kb().pfacts], key=str)
    # the sub-KB owning A ⊆ B sees the hard fact on A; the one owning B ⊆ C sees the one on C
    for s in subs:
        assert NotInSubsumptionWith(sub="A", sibling="C") in s.facts


def test_partition_keeps_pfacts_whose_entities_have_no_edges():
    kb = KB(pfacts=[PFact(fact=DisjointWith(sub="p", sibling="q"), prob=0.8)])
    subs = [s for s in partition_kb(kb) if s.pfacts]
    assert len(subs) == 1
    assert subs[0].pfacts == kb.pfacts


def test_pfact_owner_entity():
    assert pfact_owner_entity(ProperSubClassOf(sub="b", sup="a")) == "b"
    assert pfact_owner_entity(EquivalentTo(sub="b", equivalent="a")) == "b"
    assert pfact_owner_entity(NotInSubsumptionWith(sub="b", sibling="a")) == "a"


def test_partitioned_solve_respects_hard_facts_across_components():
    kb = _chain_kb()
    solution = solve(kb, SearchConfig(partition_initial_threshold=1))
    assert len(solution.solved_pfacts) == 2  # each pfact solved exactly once
    accepted = [sp.pfact.fact for sp in solution.solved_pfacts if sp.truth_value]
    assert len(accepted) == 1  # A ⊆ B and B ⊆ C together violate the hard fact
    assert NxReasoner().reason(KB(facts=kb.facts + accepted)).satisfiable
    assert solution.prior_prob == pytest.approx(0.9 * 0.1)


def test_add_carried_facts_brings_context_without_mutating():
    kb = _chain_kb()
    sub = KB(pfacts=[kb.pfacts[1]])
    extended = add_carried_facts(sub, kb, [SubClassOf(sub="A", sup="B")])
    assert SubClassOf(sub="A", sup="B") in extended.facts
    assert NotInSubsumptionWith(sub="A", sibling="C") in extended.facts
    assert sub.facts == []
    # nothing carried, nothing added
    assert add_carried_facts(sub, kb, [SubClassOf(sub="X", sup="Y")]) is sub


def test_split_connected_components_terminates_on_unsplittable_hub():
    """
    A hub with many equal-probability spokes: every pfact is owned by the hub,
    so no component fits the limit until enough spokes have been dropped. This
    used to loop forever (step size larger than the limit); it must terminate
    with every pfact yielded exactly once and no oversized part.
    """
    kb = KB(
        pfacts=[PFact(fact=EquivalentTo(sub="HUB", equivalent=f"X{i}"), prob=0.9) for i in range(150)]
    )
    parts = list(split_connected_components(kb, max_pfacts_per_clique=5))
    assert sum(len(p.pfacts) for p in parts) == 150
    assert all(0 < len(p.pfacts) <= 5 for p in parts)
