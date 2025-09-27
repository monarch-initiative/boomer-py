"""
Tests for the boomer.evaluator module.
"""
import pytest

from boomer.evaluator import evaluate_facts, EvalStats
from boomer.model import SubClassOf


def make_facts(pairs):
    """Helper to build SubClassOf facts from (sub, sup) pairs."""
    return [SubClassOf(sub=a, sup=b) for a, b in pairs]


def test_empty_lists():
    stats = evaluate_facts([], [])
    assert stats.f1 == 0.0
    assert stats.tp == 0
    assert stats.fp == 0
    assert stats.fn == 0
    assert stats.precision == 0.0
    assert stats.recall == 0.0


def test_perfect_match_order_independent():
    pairs = [("A", "B"), ("C", "D"), ("E", "F")]
    gold = make_facts(pairs)
    # reversed order in predictions
    preds = make_facts(list(reversed(pairs)))
    stats = evaluate_facts(gold, preds)
    assert stats.tp == 3
    assert stats.fp == 0
    assert stats.fn == 0
    assert stats.precision == pytest.approx(1.0)
    assert stats.recall == pytest.approx(1.0)
    assert stats.f1 == pytest.approx(1.0)


def test_partial_overlap():
    gold = make_facts([("A", "B"), ("B", "C")])
    preds = make_facts([("A", "B"), ("C", "D")])
    stats = evaluate_facts(gold, preds)
    # one true positive, one false positive, one false negative
    assert stats.tp == 1
    assert stats.fp == 1
    assert stats.fn == 1
    assert stats.precision == pytest.approx(0.5)
    assert stats.recall == pytest.approx(0.5)
    assert stats.f1 == pytest.approx(0.5)


def test_gold_only_predictions_empty():
    gold = make_facts([("X", "Y"), ("Y", "Z")])
    stats = evaluate_facts(gold, [])
    assert stats.tp == 0
    assert stats.fp == 0
    assert stats.fn == 2
    assert stats.precision == pytest.approx(0.0)
    assert stats.recall == pytest.approx(0.0)
    assert stats.f1 == pytest.approx(0.0)


def test_predictions_only_gold_empty():
    preds = make_facts([("X", "Y"), ("Y", "Z")])
    stats = evaluate_facts([], preds)
    assert stats.tp == 0
    assert stats.fp == 2
    assert stats.fn == 0
    assert stats.precision == pytest.approx(0.0)
    assert stats.recall == pytest.approx(0.0)
    assert stats.f1 == pytest.approx(0.0)


def test_duplicate_predictions_deduplicated():
    gold = make_facts([("A", "B")])
    # duplicate fact in predictions
    preds = make_facts([("A", "B"), ("A", "B")])
    stats = evaluate_facts(gold, preds)
    assert stats.tp == 1
    assert stats.fp == 0
    assert stats.fn == 0
    assert stats.precision == pytest.approx(1.0)
    assert stats.recall == pytest.approx(1.0)
    assert stats.f1 == pytest.approx(1.0)