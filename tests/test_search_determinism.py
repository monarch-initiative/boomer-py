"""Regression tests for issue #10: hash seeds must not change search results."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from boomer.model import (
    KB,
    EquivalentTo,
    MemberOfDisjointGroup,
    PFact,
    ProbabilityMissingProperSubClassOf,
    ProperSubClassOf,
    SearchConfig,
    Solution,
)
from boomer.search import solve


def make_kb() -> KB:
    """Small hierarchy alignment with the topology of the reported disease KB."""
    groups = {
        "entry": "local",
        "type1": "local",
        "type2": "local",
        "disease": "ontology",
        "parent": "ontology",
        "subtype": "ontology",
    }
    facts = [
        MemberOfDisjointGroup(sub=sub, group=group) for sub, group in groups.items()
    ]
    facts += [
        ProperSubClassOf(sub=sub, sup=sup)
        for sub, sup in [("type1", "entry"), ("type2", "entry"), ("disease", "parent")]
    ]
    pfacts = []
    for sub, target, probabilities in [
        ("entry", "disease", (0.05, 0.03, 0.9)),
        ("type1", "parent", (0.9, 0.07, 0.03)),
        ("type2", "subtype", (0.9, 0.07, 0.03)),
    ]:
        for fact, prob in zip(
            [
                EquivalentTo(sub=sub, equivalent=target),
                ProperSubClassOf(sub=sub, sup=target),
                ProperSubClassOf(sub=target, sup=sub),
            ],
            probabilities,
        ):
            pfacts.append(PFact(fact=fact, prob=prob))
    for i in range(2):
        target = f"external:{i}"
        facts.append(MemberOfDisjointGroup(sub=target, group=target))
        pfacts.append(
            PFact(fact=EquivalentTo(sub="disease", equivalent=target), prob=0.95)
        )
    return KB(facts=facts, pfacts=pfacts)


def analytical_result(solution: Solution) -> dict:
    result = solution.model_dump(
        exclude={"time_started", "time_finished", "sub_solutions"}
    )
    result["sub_solutions"] = [analytical_result(s) for s in solution.sub_solutions]
    return result


@pytest.mark.parametrize("threshold", [6, 200])
def test_hash_seed_independence(threshold: int) -> None:
    script = f"""
import contextlib, io, json, runpy
helpers = runpy.run_path({str(Path(__file__).resolve())!r})
make_kb = helpers["make_kb"]
analytical_result = helpers["analytical_result"]
from boomer.model import SearchConfig
from boomer.search import solve
kb = make_kb()
if {threshold} == 200:
    kb.pfacts = kb.pfacts[:6]
with contextlib.redirect_stdout(io.StringIO()):
    solution = solve(kb, SearchConfig(timeout_seconds=30, partition_initial_threshold={threshold}))
assert not solution.timed_out and all(not s.timed_out for s in solution.sub_solutions)
print(json.dumps(analytical_result(solution), sort_keys=True))
"""
    results = [
        json.loads(
            subprocess.run(
                [sys.executable, "-c", script],
                env={**os.environ, "PYTHONHASHSEED": seed},
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
        )
        for seed in ["0", "1", "42", "random", "random"]
    ]
    assert all(result == results[0] for result in results[1:])


def test_repeated_solve_preserves_inputs() -> None:
    kb = make_kb()
    kb.pfacts = kb.pfacts[:6]
    kb.hyperparams = [
        ProbabilityMissingProperSubClassOf(
            prob=0.2,
            disjoint_group_sub="local",
            disjoint_group_sup="local",
        )
    ]
    config = SearchConfig(timeout_seconds=30)
    original_kb = kb.model_dump()
    original_config = config.model_dump()
    with contextlib.redirect_stdout(io.StringIO()):
        results = [analytical_result(solve(kb, config)) for _ in range(3)]
    assert kb.model_dump() == original_kb
    assert config.model_dump() == original_config
    assert all(result == results[0] for result in results[1:])


def test_partitioned_timeout_is_reported() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        solution = solve(
            make_kb(), SearchConfig(timeout_seconds=0, partition_initial_threshold=6)
        )
    assert any(s.timed_out for s in solution.sub_solutions)
    assert solution.timed_out
