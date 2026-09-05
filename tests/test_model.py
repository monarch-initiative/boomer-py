import pytest

from boomer.model import HypothesisTest, Solution, SubClassOf


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
