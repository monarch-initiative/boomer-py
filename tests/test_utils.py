import pytest

from boomer.model import Solution
from boomer.utils import combine_solutions


def _solution(timed_out: bool, prior: float = 0.5) -> Solution:
    return Solution(
        number_of_combinations=1,
        number_of_satisfiable_combinations=1,
        number_of_combinations_explored_including_implicit=1,
        confidence=1.0,
        prior_prob=prior,
        posterior_prob=1.0,
        proportion_of_combinations_explored=1.0,
        ground_pfacts=[],
        solved_pfacts=[],
        time_started=0.0,
        time_finished=1.0,
        timed_out=timed_out,
    )


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([False, False], False),
        ([False, True], True),
        ([True, True], True),
    ],
)
def test_combine_solutions_propagates_timed_out(flags, expected):
    combined = combine_solutions([_solution(f) for f in flags])
    assert combined.timed_out is expected
    assert combined.number_of_components == len(flags)
    assert combined.prior_prob == pytest.approx(0.5 ** len(flags))
