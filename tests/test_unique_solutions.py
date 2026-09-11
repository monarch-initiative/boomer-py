"""Probability aggregation counts assignments once while preserving path budgets."""

import importlib
from itertools import product
from math import prod

import pytest

from boomer.model import (
    KB,
    EquivalentTo,
    MemberOfDisjointGroup,
    PFact,
    ProperSubClassOf,
    SearchConfig,
    TreeNode,
)
from boomer.reasoners import get_reasoner
from boomer.search import solve


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("tie", [False, True])
def test_probabilities_match_exhaustive_assignments(reverse, tie):
    kb = KB(
        pfacts=[
            PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
            PFact(fact=ProperSubClassOf(sub="A", sup="B"), prob=0.07),
            PFact(fact=ProperSubClassOf(sub="B", sup="A"), prob=0.03),
        ]
    )
    if tie:
        kb.facts = [
            MemberOfDisjointGroup(sub="X:1", group="X"),
            MemberOfDisjointGroup(sub="X:2", group="X"),
        ]
        kb.pfacts.extend(
            PFact(fact=EquivalentTo(sub="B", equivalent=x), prob=0.95)
            for x in ("X:1", "X:2")
        )
    if reverse:
        kb.pfacts.reverse()
    before = kb.model_dump()
    config = SearchConfig(max_candidate_solutions=0)
    reasoner = get_reasoner(config.reasoner_class)
    # Enumerate each Boolean assignment once, independently of search paths.
    worlds = {}
    for values in product([False, True], repeat=len(kb.pfacts)):
        if reasoner.reason(kb, list(enumerate(values))).satisfiable:
            worlds[values] = prod(
                pfact.prob if value else 1 - pfact.prob
                for pfact, value in zip(kb.pfacts, values)
            )
    assert len(worlds) == (12 if tie else 4)
    total = sum(worlds.values())
    ranked = sorted(worlds.values(), reverse=True)
    solution = solve(kb, config)
    assert solution.number_of_satisfiable_combinations == len(worlds)
    assert solution.confidence == pytest.approx(0.5 if tie else 0.9)
    assert solution.confidence == pytest.approx(ranked[0] / sum(ranked[:2]))
    assert solution.prior_prob == pytest.approx(ranked[0])
    assert solution.posterior_prob == pytest.approx(ranked[0] / total)
    assignment = tuple(f.truth_value for f in solution.solved_pfacts)
    assert worlds[assignment] == pytest.approx(ranked[0])
    for index, fact in enumerate(solution.solved_pfacts):
        expected = sum(pr for values, pr in worlds.items() if values[index]) / total
        assert fact.posterior_prob == pytest.approx(expected)
    assert kb.model_dump() == before


@pytest.mark.parametrize("cap", [0, 2, 3])
@pytest.mark.parametrize("prior", [0.5, 0.8])
def test_scoring_deduplicates_without_changing_raw_effort_cap(monkeypatch, cap, prior):
    kb = KB(
        pfacts=[
            PFact(fact=EquivalentTo(sub="a", equivalent="b"), prob=prior),
            PFact(fact=EquivalentTo(sub="c", equivalent="d"), prob=0.9),
        ]
    )

    def node(selections, probability):
        return TreeNode(
            selections=selections,
            asserted_selections=selections,
            terminal=True,
            pr=probability,
            pr_selected=probability,
        )

    nodes = [
        node([(0, True), (1, True)], prior * 0.9),
        node([(1, True), (0, True)], prior * 0.9),
        node([(0, False), (1, True)], (1 - prior) * 0.9),
        node([(0, True), (1, False)], 0.0),  # Unsatisfiable raw terminal node.
    ]
    visited = []

    def search(*args):
        for n in nodes:
            visited.append(n)
            yield n

    monkeypatch.setattr(importlib.import_module("boomer.search"), "search", search)
    solution = solve(kb, SearchConfig(max_candidate_solutions=cap))
    expected_paths = cap or len(nodes)
    assert len(visited) == expected_paths
    assert solution.number_of_combinations == expected_paths
    assert solution.number_of_combinations_explored_including_implicit == expected_paths
    assert solution.number_of_satisfiable_combinations == (1 if cap == 2 else 2)
    # With cap=2, both raw paths reach the same solution; no runner-up was found.
    expected_confidence = 1.0 if cap == 2 else prior
    assert solution.confidence == pytest.approx(expected_confidence)
    assert solution.posterior_prob == pytest.approx(expected_confidence)
    assert solution.solved_pfacts[0].posterior_prob == pytest.approx(
        expected_confidence
    )
