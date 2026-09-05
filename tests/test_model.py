import pytest

from boomer.model import (
    KB,
    DisjointWith,
    EquivalentTo,
    HypothesisTest,
    NegatedFact,
    OneOf,
    PFact,
    ProbabilityMissingEquivalentTo,
    ProbabilityMissingProperSubClassOf,
    Solution,
    SubClassOf,
    canonical_fact,
    dedupe_pfacts,
)


def _solution(prior: float) -> Solution:
    return Solution(
        number_of_combinations=1,
        number_of_satisfiable_combinations=1 if prior > 0 else 0,
        number_of_combinations_explored_including_implicit=1,
        confidence=0.0,
        prior_prob=prior,
        posterior_prob=0.0,
        proportion_of_combinations_explored=1.0,
        ground_pfacts=[],
        solved_pfacts=[],
    )


@pytest.mark.parametrize(
    "pos,neg,expected",
    [
        (0.3, 0.1, 0.75),
        (0.0, 0.4, 0.0),
        (0.0, 0.0, 0.0),
    ],
)
def test_hypothesis_test_probability(pos, neg, expected):
    ht = HypothesisTest(
        hypothesis=SubClassOf(sub="a", sup="b"),
        solution_pos=_solution(pos),
        solution_neg=_solution(neg),
    )
    assert ht.probability == pytest.approx(expected)


@pytest.mark.parametrize(
    "fact,expected",
    [
        (EquivalentTo(sub="b", equivalent="a"), EquivalentTo(sub="a", equivalent="b")),
        (EquivalentTo(sub="a", equivalent="b"), EquivalentTo(sub="a", equivalent="b")),
        (DisjointWith(sub="b", sibling="a"), DisjointWith(sub="a", sibling="b")),
        (
            NegatedFact(negated=EquivalentTo(sub="b", equivalent="a")),
            NegatedFact(negated=EquivalentTo(sub="a", equivalent="b")),
        ),
        (SubClassOf(sub="b", sup="a"), SubClassOf(sub="b", sup="a")),
    ],
)
def test_canonical_fact(fact, expected):
    assert canonical_fact(fact) == expected


def test_dedupe_pfacts_keeps_max_and_first_orientation():
    pfacts = [
        PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.7),
        PFact(fact=SubClassOf(sub="a", sup="c"), prob=0.5),
        PFact(fact=EquivalentTo(sub="b", equivalent="a"), prob=0.9),
        PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.6),
    ]
    assert dedupe_pfacts(pfacts) == [
        PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.9),
        PFact(fact=SubClassOf(sub="a", sup="c"), prob=0.5),
    ]


def test_kb_extend_keeps_multi_labeled_edges_until_deduped():
    kb = KB(pfacts=[PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.7)])
    merged = kb.extend(pfacts=[PFact(fact=EquivalentTo(sub="b", equivalent="a"), prob=0.8)])
    # both copies survive the merge: they act as independent evidence in the search
    assert len(merged.pfacts) == 2
    assert merged.dedupe_pfacts() == 1
    assert merged.pfacts == [PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=0.8)]
    # the original is untouched
    assert len(kb.pfacts) == 1 and kb.pfacts[0].prob == 0.7


def test_oneof_round_trips_through_the_fact_union():
    kb = KB(facts=[OneOf(sub="a", sibling="b")])
    assert KB.model_validate_json(kb.model_dump_json()).facts == kb.facts


def test_hyperparameters_round_trip_with_their_fields():
    kb = KB(
        hyperparams=[
            ProbabilityMissingProperSubClassOf(prob=0.2, disjoint_group_sub="A", disjoint_group_sup="B"),
            ProbabilityMissingEquivalentTo(prob=0.1, disjoint_group_sub="A", disjoint_group_equivalent="B"),
        ]
    )
    restored = KB.model_validate_json(kb.model_dump_json())
    assert restored.hyperparams == kb.hyperparams
    assert isinstance(restored.hyperparams[0], ProbabilityMissingProperSubClassOf)
