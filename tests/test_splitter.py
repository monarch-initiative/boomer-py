import pytest
import boomer.datasets.diagonal as diagonal
from boomer.model import (
    KB,
    PFact,
    EquivalentTo,
    ProperSubClassOf,
    MemberOfDisjointGroup,
)
from boomer.splitter import extract_neighborhood, split_connected_components


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
