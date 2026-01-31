"""Tests for grid search with aggregation and synthesis."""

import pytest
from boomer.model import (
    KB,
    PFact,
    EquivalentTo,
    ProperSubClassOf,
    MemberOfDisjointGroup,
    SearchConfig,
    GridSearch,
    GridSearchResult,
    EvalStats,
)
from boomer.search import (
    grid_search,
    compute_aggregate_stats,
    synthesize_solution,
    find_best_config,
    find_pareto_frontier,
)


@pytest.fixture
def simple_kb():
    """Create a simple KB for testing."""
    return KB(
        facts=[
            MemberOfDisjointGroup(sub="A", group="G1"),
            MemberOfDisjointGroup(sub="B", group="G1"),
            MemberOfDisjointGroup(sub="X", group="G2"),
            MemberOfDisjointGroup(sub="Y", group="G2"),
        ],
        pfacts=[
            PFact(fact=EquivalentTo(sub="A", equivalent="X"), prob=0.9),
            PFact(fact=EquivalentTo(sub="B", equivalent="Y"), prob=0.85),
            PFact(fact=EquivalentTo(sub="A", equivalent="Y"), prob=0.1),
            PFact(fact=ProperSubClassOf(sub="A", sup="B"), prob=0.3),
        ],
    )


@pytest.fixture
def eval_kb():
    """Ground truth for evaluation."""
    return KB(
        facts=[
            EquivalentTo(sub="A", equivalent="X"),
            EquivalentTo(sub="B", equivalent="Y"),
        ]
    )


def test_grid_search_with_aggregation(simple_kb, eval_kb):
    """Test that grid search produces aggregate stats and synthesized solution."""
    grid = GridSearch(
        configurations=[
            SearchConfig(max_iterations=1000, partition_initial_threshold=10),
            SearchConfig(max_iterations=500, partition_initial_threshold=5),
        ],
        configuration_matrix={
            "max_pfacts_per_clique": [10, 20],
        }
    )

    result = grid_search(simple_kb, grid, eval_kb)

    # Check that all aggregation fields are populated
    assert result.results is not None
    assert len(result.results) == 4  # 2 base configs × 2 clique values
    assert result.aggregate_stats is not None
    assert result.synthesized_solution is not None
    assert result.best_config is not None
    assert result.best_config_metric is not None
    assert result.pareto_frontier is not None


def test_compute_aggregate_stats(simple_kb):
    """Test aggregate statistics computation."""
    from boomer.search import solve

    # Create multiple results with different configs
    configs = [
        SearchConfig(max_iterations=1000, timeout_seconds=10),
        SearchConfig(max_iterations=500, timeout_seconds=5),
        SearchConfig(max_iterations=2000, timeout_seconds=20),
    ]

    results = []
    for cfg in configs:
        sol = solve(simple_kb, cfg)
        # Create mock evaluation stats
        eval_stats = EvalStats(
            tp=2, fp=0, fn=0,
            precision=1.0, recall=1.0, f1=1.0
        )
        results.append(GridSearchResult(config=cfg, result=sol, evaluation=eval_stats))

    stats = compute_aggregate_stats(results)

    assert stats.mean_precision == 1.0
    assert stats.mean_recall == 1.0
    assert stats.mean_f1 == 1.0
    assert stats.std_precision == 0.0
    assert stats.success_rate == 1.0
    assert stats.timeout_rate == 0.0
    assert stats.mean_confidence > 0
    assert stats.mean_combinations_explored > 0


def test_synthesize_solution(simple_kb):
    """Test solution synthesis across multiple configurations."""
    from boomer.search import solve

    # Run with different configs to get variation
    configs = [
        SearchConfig(max_iterations=1000),
        SearchConfig(max_iterations=500),
        SearchConfig(max_iterations=100),
    ]

    results = []
    for cfg in configs:
        sol = solve(simple_kb, cfg)
        results.append(GridSearchResult(config=cfg, result=sol))

    synthesized = synthesize_solution(simple_kb, results)

    assert synthesized is not None
    assert len(synthesized.pfact_consensus) == len(simple_kb.pfacts)
    assert synthesized.contributing_configs == 3
    assert synthesized.aggregation_method == "weighted_vote"

    # Check that consensus scores are computed
    for consensus in synthesized.pfact_consensus:
        assert 0 <= consensus.acceptance_rate <= 1
        assert 0 <= consensus.consensus_score <= 1
        assert consensus.configurations_total == 3

    # High confidence facts should have high acceptance rate
    for pfact in synthesized.high_confidence_facts:
        # Find corresponding consensus
        consensus = next(
            c for c in synthesized.pfact_consensus
            if c.pfact == pfact
        )
        assert consensus.consensus_score > 0.8


def test_find_best_config():
    """Test finding the best configuration."""
    from boomer.model import Solution

    # Create mock results with different F1 scores
    results = []
    for i, f1 in enumerate([0.8, 0.9, 0.85]):
        cfg = SearchConfig(max_iterations=1000 * (i + 1))
        sol = Solution(
            number_of_combinations=100,
            number_of_satisfiable_combinations=80,
            number_of_combinations_explored_including_implicit=10,
            confidence=0.9,
            prior_prob=0.5,
            posterior_prob=0.8,
            proportion_of_combinations_explored=0.1,
            ground_pfacts=[],
            solved_pfacts=[],
        )
        eval_stats = EvalStats(
            tp=8, fp=2, fn=0,
            precision=0.8, recall=1.0, f1=f1
        )
        results.append(GridSearchResult(config=cfg, result=sol, evaluation=eval_stats))

    best_cfg, metric = find_best_config(results)

    assert best_cfg is not None
    assert best_cfg.max_iterations == 2000  # Config with F1=0.9
    assert metric == "f1_score"


def test_find_best_config_no_eval():
    """Test finding best config when no evaluation available."""
    from boomer.model import Solution

    # Create results with only confidence scores
    results = []
    for i, conf in enumerate([0.7, 0.95, 0.8]):
        cfg = SearchConfig(max_iterations=1000 * (i + 1))
        sol = Solution(
            number_of_combinations=100,
            number_of_satisfiable_combinations=80,
            number_of_combinations_explored_including_implicit=10,
            confidence=conf,
            prior_prob=0.5,
            posterior_prob=0.8,
            proportion_of_combinations_explored=0.1,
            ground_pfacts=[],
            solved_pfacts=[],
        )
        results.append(GridSearchResult(config=cfg, result=sol))

    best_cfg, metric = find_best_config(results)

    assert best_cfg is not None
    assert best_cfg.max_iterations == 2000  # Config with confidence=0.95
    assert metric == "confidence"


def test_find_pareto_frontier():
    """Test Pareto frontier identification."""
    from boomer.model import Solution

    # Create results with different speed/accuracy trade-offs
    # (time, f1) pairs
    configs_data = [
        (1.0, 0.9),   # Fast and good - on frontier
        (0.5, 0.85),  # Faster but worse - on frontier
        (2.0, 0.91),  # Slower but better - on frontier
        (1.5, 0.88),  # Dominated by (1.0, 0.9)
        (3.0, 0.89),  # Dominated by (2.0, 0.91)
    ]

    results = []
    for i, (time, f1) in enumerate(configs_data):
        cfg = SearchConfig(max_iterations=1000 + i)
        sol = Solution(
            number_of_combinations=100,
            number_of_satisfiable_combinations=80,
            number_of_combinations_explored_including_implicit=10,
            confidence=f1,  # Use f1 as confidence proxy
            prior_prob=0.5,
            posterior_prob=0.8,
            proportion_of_combinations_explored=0.1,
            ground_pfacts=[],
            solved_pfacts=[],
            time_started=0.0,
            time_finished=time,
        )
        eval_stats = EvalStats(
            tp=int(f1 * 10), fp=10 - int(f1 * 10), fn=0,
            precision=f1, recall=f1, f1=f1
        )
        results.append(GridSearchResult(config=cfg, result=sol, evaluation=eval_stats))

    frontier = find_pareto_frontier(results)

    # Should contain the non-dominated configs
    assert len(frontier) == 3
    frontier_configs = [r.config.max_iterations for r in frontier]
    assert 1000 in frontier_configs  # Fast and good
    assert 1001 in frontier_configs  # Faster but worse
    assert 1002 in frontier_configs  # Slower but better


@pytest.mark.parametrize("n_configs,n_pfacts", [
    (2, 3),
    (3, 5),
    (5, 10),
])
def test_grid_search_scaling(n_configs, n_pfacts):
    """Test grid search with varying numbers of configurations and pfacts."""
    kb = KB(
        pfacts=[
            PFact(fact=EquivalentTo(sub=f"A{i}", equivalent=f"B{i}"), prob=0.5 + i * 0.1)
            for i in range(n_pfacts)
        ]
    )

    configs = [
        SearchConfig(max_iterations=100 * (i + 1))
        for i in range(n_configs)
    ]

    grid = GridSearch(configurations=configs)
    result = grid_search(kb, grid)

    assert len(result.results) == n_configs
    assert result.aggregate_stats is not None
    assert result.synthesized_solution is not None
    assert len(result.synthesized_solution.pfact_consensus) == n_pfacts


def test_consensus_categorization(simple_kb):
    """Test that facts are properly categorized by consensus strength."""
    from boomer.search import solve

    # Create results that will produce different consensus levels
    results = []

    # Config that accepts high-prob facts
    cfg1 = SearchConfig(max_iterations=10000)
    sol1 = solve(simple_kb, cfg1)
    results.append(GridSearchResult(config=cfg1, result=sol1))

    # Config with limited search that might miss some facts
    cfg2 = SearchConfig(max_iterations=10)
    sol2 = solve(simple_kb, cfg2)
    results.append(GridSearchResult(config=cfg2, result=sol2))

    synthesized = synthesize_solution(simple_kb, results)

    # Check categorization
    assert isinstance(synthesized.high_confidence_facts, list)
    assert isinstance(synthesized.uncertain_facts, list)

    # High confidence facts should have the highest prior probabilities
    if synthesized.high_confidence_facts:
        high_conf_probs = [pf.prob for pf in synthesized.high_confidence_facts]
        assert all(p >= 0.8 for p in high_conf_probs), "High confidence should be high probability facts"


def test_aggregate_stats_with_timeouts(simple_kb):
    """Test aggregate stats correctly handle timeouts."""
    from boomer.model import Solution

    results = []

    # Normal result
    sol1 = Solution(
        number_of_combinations=100,
        number_of_satisfiable_combinations=80,
        number_of_combinations_explored_including_implicit=10,
        confidence=0.9,
        prior_prob=0.5,
        posterior_prob=0.8,
        proportion_of_combinations_explored=0.1,
        ground_pfacts=[],
        solved_pfacts=[],
        timed_out=False,
        time_started=0,
        time_finished=1,
    )
    results.append(GridSearchResult(config=SearchConfig(), result=sol1))

    # Timed out result
    sol2 = Solution(
        number_of_combinations=50,
        number_of_satisfiable_combinations=40,
        number_of_combinations_explored_including_implicit=5,
        confidence=0.7,
        prior_prob=0.4,
        posterior_prob=0.6,
        proportion_of_combinations_explored=0.05,
        ground_pfacts=[],
        solved_pfacts=[],
        timed_out=True,
        time_started=0,
        time_finished=10,
    )
    results.append(GridSearchResult(config=SearchConfig(), result=sol2))

    stats = compute_aggregate_stats(results)

    assert stats.timeout_rate == 0.5  # 1 out of 2 timed out
    assert stats.success_rate == 1.0  # Both have confidence > 0
    assert stats.mean_time == 5.5  # (1 + 10) / 2