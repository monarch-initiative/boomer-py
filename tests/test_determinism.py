"""
Regression test for hash-seed independence of the solver (issue #10).

Set/dict iteration order over hashed Fact models used to leak into the
order in which selection probabilities were multiplied, which changed
float tie-breaks in the search stack and therefore which terminal nodes
were reached under an iteration budget. Each subprocess below runs the
same bounded search under a different PYTHONHASHSEED; all must agree.
"""

import json
import os
import subprocess
import sys

import pytest

SCRIPT = """
import json
from boomer.datasets.false_bridge import kb
from boomer.model import SearchConfig
from boomer.search import solve

s = solve(kb, SearchConfig(max_iterations=75))
print(json.dumps({
    "combinations": s.number_of_combinations,
    "satisfiable": s.number_of_satisfiable_combinations,
    "accepted": sorted(str(sp.pfact.fact) for sp in s.solved_pfacts if sp.truth_value),
    "posteriors": [round(sp.posterior_prob, 12) for sp in s.solved_pfacts],
}))
"""


def _solve_under_seed(seed: str) -> dict:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    proc = subprocess.run(
        [sys.executable, "-c", SCRIPT], env=env, capture_output=True, text=True, check=True
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def baseline() -> dict:
    return _solve_under_seed("0")


@pytest.mark.parametrize("seed", ["3", "5", "7"])
def test_solve_is_independent_of_hash_seed(seed: str, baseline: dict):
    assert _solve_under_seed(seed) == baseline
