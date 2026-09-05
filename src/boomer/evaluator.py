"""
Evaluation of predicted Facts against target Facts.

This module provides functionality to compute precision, recall, and F1-score
for predicted ontology facts.
"""
import json
from typing import Iterable, Set

from boomer.model import KB, Fact, EvalStats, canonical_fact
from boomer.reasoners.nx_reasoner import NxReasoner


def evaluate_facts(
    target_facts: list[Fact], predicted_facts: list[Fact], types: list[str] | None = None,
) -> EvalStats:
    """
    Compare target (gold) facts with predicted facts and compute evaluation metrics.

    A prediction that is entailed by the target facts counts as a true positive
    even when it is not stated explicitly, and symmetric facts match regardless
    of argument order. The caller's lists are not modified.

    Args:
        target_facts: Iterable of ground-truth Fact objects.
        predicted_facts: Iterable of predicted Fact objects.
        types: Iterable of types of facts to evaluate.

    Returns:
        EvalStats containing true positives (tp), false positives (fp),
        false negatives (fn), precision, recall, and f1-score.

    Examples:
        >>> from boomer.model import SubClassOf
        >>> from boomer.evaluator import evaluate_facts, EvalStats
        >>> gold = [SubClassOf(sub="A", sup="B"), SubClassOf(sub="B", sup="C")]
        >>> preds = [SubClassOf(sub="A", sup="B"), SubClassOf(sub="C", sup="D")]
        >>> stats = evaluate_facts(gold, preds)
        >>> stats.tp
        1
        >>> stats.fp
        1
        >>> stats.fn
        1
        >>> stats.precision
        0.5

        >>> # A ⊆ C follows from the gold facts, so predicting it is not a false positive
        >>> stats = evaluate_facts(gold, [SubClassOf(sub="A", sup="C")])
        >>> (stats.tp, stats.fp)
        (1, 0)
        >>> len(gold)
        2

        >>> evaluate_facts([], [])
        EvalStats(tp=0, fp=0, fn=0, tp_list=[], fp_list=[], fn_list=[], precision=0.0, recall=0.0, f1=0.0)
    """
    target_facts = list(target_facts)
    predicted_facts = list(predicted_facts)
    target_kb = KB(facts=target_facts)
    reasoner = NxReasoner()

    def _to_key(fact: Fact) -> str:
        return json.dumps(canonical_fact(fact).model_dump(), sort_keys=True)
    
    def _filter_facts(facts: list[Fact], types: list[str] | None = None) -> Iterable[Fact]:
        if not types:
            return facts
        return [fact for fact in facts if type(fact).__name__ in types]
    
    def _to_key_set(facts: Iterable[Fact]) -> Set[str]:
        return {_to_key(fact) for fact in facts}
    
    # predictions entailed by the gold facts are counted as gold (the target is
    # assumed to be saturated with respect to the predictions)
    for fact, tv in reasoner.reason(target_kb, additional_hypotheses=predicted_facts).entailed_hypotheses:
        if tv:
            target_facts.append(fact)

    k2fact = {_to_key(fact): fact for fact in target_facts + predicted_facts}

    target_set = _to_key_set(_filter_facts(target_facts, types))
    pred_set = _to_key_set(_filter_facts(predicted_facts, types))

    tp_list = list(target_set & pred_set)
    fp_list = list(pred_set - target_set)
    fn_list = list(target_set - pred_set)

    tp = len(tp_list)
    fp = len(fp_list)
    fn = len(fn_list)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0


    def _to_fact_list(keys: Iterable[str]) -> list[Fact]:
        return [k2fact[k] for k in keys]

    return EvalStats(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1, tp_list=_to_fact_list(tp_list), fp_list=_to_fact_list(fp_list), fn_list=_to_fact_list(fn_list))