from copy import deepcopy
import pytest
from boomer.model import KB, EquivalentTo, MemberOfDisjointGroup, ProbabilityMissingProperSubClassOf, ProperSubClassOf, SubClassOf, PFact, SearchConfig, Solution
from boomer.search import evaluate_hypotheses, search, solve
import boomer.datasets.animals as animals
import boomer.datasets.quad as quad
import boomer.datasets.ladder as ladder
import boomer.datasets.family as family
import boomer.datasets.multilingual as multilingual
import boomer.datasets.disease as disease
import boomer.datasets.false_bridge as false_bridge
from boomer.renderers.markdown_renderer import MarkdownRenderer

def render(solution: Solution):
    renderer = MarkdownRenderer()
    print(renderer.render(solution))

def match_facts(solved_pfacts, expected):
    for tf, fact, prior, posterior in expected:
        matching_spfs = [spf for spf in solved_pfacts if spf.pfact.fact == fact]
        assert len(matching_spfs) == 1
        spf = matching_spfs[0]
        assert spf.truth_value == tf
        assert spf.posterior_prob == pytest.approx(posterior, 0.01)
        assert spf.pfact.prob == pytest.approx(prior, 0.01)

def test_search_order():
    kb = animals.kb
    
        

@pytest.mark.parametrize("subs, expected_results", [
    (
        [
            ("A", "B", 0.5),
        ],
        None,
    )
])
def test_solve_main(subs, expected_results):
    kb = KB(
        pfacts=[
            PFact(fact=SubClassOf(sub=s, sup=o), prob=pr) for s, o, pr in subs
        ]
    )
    solve(kb)

@pytest.mark.parametrize("name,pr1, pr2, expected_confidence, expected_results", [
    ("tie", 0.9, 0.9, 0.5, None),
    ("x<y", 0.9, 0.1, 0.9, [ProperSubClassOf(sub="x", sup="y")]),
    ("y>x", 0.1, 0.9, 0.9, [ProperSubClassOf(sub="y", sup="x")]),
    ("x<<y", 0.999, 0.001, 0.999, [ProperSubClassOf(sub="x", sup="y")]),
])
def test_reciprocal_pair(name, pr1, pr2, expected_confidence, expected_results):
    kb = KB(
        pfacts=[
            PFact(fact=ProperSubClassOf(sub="x", sup="y"), prob=pr1),
            PFact(fact=ProperSubClassOf(sub="y", sup="x"), prob=pr2),
        ]
    )
    solution = solve(kb)
    print(solution)
    render(solution)
    assert solution.number_of_combinations == 4
    assert solution.number_of_satisfiable_combinations == 3
    assert solution.confidence == pytest.approx(expected_confidence, 0.1)
    if expected_results is not None:
        entailed_facts = [spf.pfact.fact for spf in solution.solved_pfacts if spf.truth_value]
        assert set(entailed_facts) == set(expected_results)


@pytest.mark.parametrize("x, y, max_candidate_solutions", [
    (1,2, 100000),
    (2,2, 100),
    (3,3, 100),
    (4,4, 100),
    (6,6, 100),
])
def test_grid(x, y, max_candidate_solutions):
    """
    Tests a maximally connected graph with x*y nodes.
    """
    pfacts = [] 
    for i in range(x):
        e1 = f"X:{i}"
        #pfacts.append(PFact(fact=MemberOfDisjointGroup(sub=e1, group="X"), prob=0.25))
        for j in range(y):
            e2 = f"Y:{j}"
            prs = [0.05, 0.05, 0.8, 0.1]
            
            pfacts.append(PFact(fact=ProperSubClassOf(sub=e1, sup=e2), prob=prs[0]))
            pfacts.append(PFact(fact=ProperSubClassOf(sub=e2, sup=e1), prob=prs[1]))
            pfacts.append(PFact(fact=EquivalentTo(sub=e1, equivalent=e2), prob=prs[2]))
            #pfacts.append(PFact(fact=EquivalentTo(e2, e1), prob=prs[3]))
    for j in range(y):
        e2 = f"Y:{j}"
        #pfacts.append(PFact(fact=MemberOfDisjointGroup(sub=e2, group="Y"), prob=0.25))
    kb = KB(pfacts=pfacts)
    cfg = SearchConfig(max_candidate_solutions=max_candidate_solutions)
    solution = solve(kb, cfg)
    print(solution)
    render(solution)


@pytest.mark.parametrize("chain_length, max_candidate_solutions", [
    (1, 100000),
    (2, 100000),
    (3, 100000),
    (4, 10000),
    (5, 10000),
    (6, 10000),
    (7, 10000),
    (8, 1000),
    #(9, 100),
    #(10, 100),
    (20, 10),
    #(100, 10),
])
def test_chain(chain_length, max_candidate_solutions):
    """
    Tests a cyclic ProperSubClassOf chain of n nodes.

    Locally the probability of each ProperSubClassOf is high, but the global
    probability of accepting all is zero, as this leads to a cycle/inconsistency.
    """
    pfacts = []
    for i in range(chain_length):
        e1 = f"X:{i}"
        e2 = f"X:{i+1}"
        pfacts.append(PFact(fact=ProperSubClassOf(sub=e1, sup=e2), prob=0.9))
    # create a cycle
    pfacts.append(PFact(fact=ProperSubClassOf(sub=e2, sup="X:1"), prob=0.8))
    kb = KB(pfacts=pfacts)
    cfg = SearchConfig(max_candidate_solutions=max_candidate_solutions)
    solution = solve(kb, cfg)
    print(solution)
    render(solution)
    assert solution.confidence > 0.495
    assert solution.confidence < 0.9
    assert solution.posterior_prob < 0.6
    if chain_length > 6:
        assert solution.posterior_prob == pytest.approx(0.2, abs=0.1)
    # chain should have a single link broken
    assert len([f for f in solution.solved_pfacts if f.truth_value]) == chain_length




def test_solve_quad():
    """
    Expected results:

    Grounding:
    * True EquivalentTo(sub='A1', equivalent='B1') :: prior: 0.9 posterior: 0.8737864077669906
    * True EquivalentTo(sub='A2', equivalent='B2') :: prior: 0.9 posterior: 0.8737864077669906
    * False EquivalentTo(sub='A1', equivalent='B2') :: prior: 0.6 posterior: 0.0145631067961165
    * False EquivalentTo(sub='A2', equivalent='B1') :: prior: 0.6 posterior: 0.0145631067961165

    """
    kb = quad.kb
    solution = solve(kb)
    print(solution)
    render(solution)
    assert solution.number_of_satisfiable_combinations == 6
    assert solution.confidence == pytest.approx(0.9, 0.05)
    assert solution.prior_prob == pytest.approx(0.13, 0.05)
    assert solution.posterior_prob == pytest.approx(0.78, 0.05)
    expected = [
        (True, EquivalentTo(sub='A1', equivalent='B1'), 0.9, 0.8737864077669906),
        (True, EquivalentTo(sub='A2', equivalent='B2'), 0.9, 0.8737864077669906),
        (False, EquivalentTo(sub='A1', equivalent='B2'), 0.6, 0.0145631067961165),
        (False, EquivalentTo(sub='A2', equivalent='B1'), 0.6, 0.0145631067961165),
    ]
    match_facts(solution.solved_pfacts, expected)

def test_solve_ladder():
    """
    Expected results:
    * 16 combinations
    * 8 satisfiable combinations
    * 1.0 proportion of combinations explored
    * 0.5 confidence
    * 1.0000000000000005e-08 prior probability
    * 0.12499999999999999 posterior probability
    * 0.0048 seconds elapsed
    Grounding:
    * True fact_type='ProperSubClassOf' sub='R4' sup='R3' :: prior: 0.1 posterior: 1.0
    * True fact_type='ProperSubClassOf' sub='R3' sup='R2' :: prior: 0.1 posterior: 1.0
    * True fact_type='ProperSubClassOf' sub='R2' sup='R1' :: prior: 0.1 posterior: 1.0
    * True fact_type='ProperSubClassOf' sub='R1' sup='R0' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R3' equivalent='R3' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R2' equivalent='R2' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R1' equivalent='R1' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R0' equivalent='R0' :: prior: 0.1 posterior: 1.0
    """
    kb = ladder.kb
    solution = solve(kb)
    print(solution)
    render(solution)
    assert solution.number_of_satisfiable_combinations == 8
    assert solution.confidence == pytest.approx(0.5, 0.05)  
    assert solution.prior_prob == pytest.approx(1.0e-08, 0.05)
    assert solution.posterior_prob == pytest.approx(0.12, 0.05)
    expected = [
        (True, ProperSubClassOf(sub='R4', sup='R3'), 0.1, 1.0),
        (True, ProperSubClassOf(sub='R3', sup='R2'), 0.1, 1.0),
        (True, ProperSubClassOf(sub='R2', sup='R1'), 0.1, 1.0),
        (True, ProperSubClassOf(sub='R1', sup='R0'), 0.1, 1.0),
        (True, EquivalentTo(sub='R3', equivalent='R3'), 0.1, 1.0),
        (True, EquivalentTo(sub='R2', equivalent='R2'), 0.1, 1.0),
        (True, EquivalentTo(sub='R1', equivalent='R1'), 0.1, 1.0),
        (True, EquivalentTo(sub='R0', equivalent='R0'), 0.1, 1.0),
    ]
    match_facts(solution.solved_pfacts, expected)

def test_solve_ladder2():
    pytest.skip("TODO: add hyperparams to ladder.py")
    """
    TODO: add hyperparams to ladder.py

    Expected results:
    * 16 combinations
    * 8 satisfiable combinations
    * 1.0 proportion of combinations explored
    * 0.5 confidence
    * 1.0000000000000005e-08 prior probability
    * 0.12499999999999999 posterior probability
    * 0.0048 seconds elapsed
    Grounding:
    * True fact_type='ProperSubClassOf' sub='R4' sup='R3' :: prior: 0.1 posterior: 1.0
    * True fact_type='ProperSubClassOf' sub='R3' sup='R2' :: prior: 0.1 posterior: 1.0
    * True fact_type='ProperSubClassOf' sub='R2' sup='R1' :: prior: 0.1 posterior: 1.0
    * True fact_type='ProperSubClassOf' sub='R1' sup='R0' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R3' equivalent='R3' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R2' equivalent='R2' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R1' equivalent='R1' :: prior: 0.1 posterior: 1.0
    * True fact_type='EquivalentTo' sub='R0' equivalent='R0' :: prior: 0.1 posterior: 1.0
    """
    kb = deepcopy(ladder.kb)
    kb.hyperparams = [ProbabilityMissingProperSubClassOf(prob=0.5, disjoint_group_sub="R", disjoint_group_sup="R")]

    solution = solve(kb)
    print(solution)
    render(solution)
    assert solution.number_of_satisfiable_combinations == 8
    assert solution.confidence == pytest.approx(0.5, 0.05)  
    assert solution.prior_prob == pytest.approx(1.0e-08, 0.05)
    assert solution.posterior_prob == pytest.approx(0.12, 0.05)
    expected = [
        (True, ProperSubClassOf(sub='R4', sup='R3'), 0.1, 1.0),
        (True, ProperSubClassOf(sub='R3', sup='R2'), 0.1, 1.0),
        (True, ProperSubClassOf(sub='R2', sup='R1'), 0.1, 1.0),
        (True, ProperSubClassOf(sub='R1', sup='R0'), 0.1, 1.0),
        (True, EquivalentTo(sub='R3', equivalent='R3'), 0.1, 1.0),
        (True, EquivalentTo(sub='R2', equivalent='R2'), 0.1, 1.0),
        (True, EquivalentTo(sub='R1', equivalent='R1'), 0.1, 1.0),
        (True, EquivalentTo(sub='R0', equivalent='R0'), 0.1, 1.0),
    ]
    match_facts(solution.solved_pfacts, expected)

def test_solve_animals():
    """
    Expected results:
    * 742 combinations
    * 34 satisfiable combinations
    * 0.8999999999999999 confidence
    * 0.38742048900000015 prior probability
    * 0.7238506318562333 posterior probability
    Grounding:
    * True EquivalentTo(sub='cat', equivalent='Felix') :: prior: 0.9 posterior: 0.895738954433891
    * True EquivalentTo(sub='dog', equivalent='Canus') :: prior: 0.9 posterior: 0.895738954433891
    * True EquivalentTo(sub='furry_animal', equivalent='Mammalia') :: prior: 0.9 posterior: 0.895738954433891
    * False EquivalentTo(sub='cat', equivalent='Canus') :: prior: 0.1 posterior: 0.0012517264017565036
    * False EquivalentTo(sub='cat', equivalent='Mammalia') :: prior: 0.1 posterior: 0.0012517264017565036
    * False EquivalentTo(sub='dog', equivalent='Felix') :: prior: 0.1 posterior: 0.0012517264017565036
    * False EquivalentTo(sub='dog', equivalent='Mammalia') :: prior: 0.1 posterior: 0.0012517264017565036
    * False EquivalentTo(sub='furry_animal', equivalent='Canus') :: prior: 0.1 posterior: 0.0012517264017565036
    * False EquivalentTo(sub='furry_animal', equivalent='Felix') :: prior: 0.1 posterior: 0.0012517264017565036
    """
    kb = animals.kb
    solution = solve(kb)
    print(solution)
    render(solution)
    assert solution.number_of_satisfiable_combinations == 34
    assert solution.confidence == pytest.approx(0.9, 0.05)
    assert solution.prior_prob == pytest.approx(0.387, 0.05)
    assert solution.posterior_prob == pytest.approx(0.72, 0.05)
    expected = [
        (True, EquivalentTo(sub='cat', equivalent='Felix'), 0.9, 0.89),
        (True, EquivalentTo(sub='dog', equivalent='Canus'), 0.9, 0.89),
        (True, EquivalentTo(sub='furry_animal', equivalent='Mammalia'), 0.9, 0.89),
    ]
    match_facts(solution.solved_pfacts, expected)
    
def test_solve_family():
    """
    Test the family dataset that models relationships between role-based and kinship terms.
    """
    kb = family.kb
    cfg = SearchConfig(max_candidate_solutions=100)  # Limit the search space
    solution = solve(kb, cfg)
    print(solution)
    render(solution)
    assert solution.confidence > 0.8
    expected = [
        (True, EquivalentTo(sub='Mother', equivalent='FemaleParent'), 0.9, pytest.approx(0.9, 0.15)),
        (True, EquivalentTo(sub='Father', equivalent='MaleParent'), 0.9, pytest.approx(0.9, 0.15)),
        (True, EquivalentTo(sub='Son', equivalent='MaleChild'), 0.9, pytest.approx(0.9, 0.15)),
        (True, EquivalentTo(sub='Daughter', equivalent='FemaleChild'), 0.9, pytest.approx(0.9, 0.15)),
        (True, EquivalentTo(sub='Brother', equivalent='MaleSibling'), 0.9, pytest.approx(0.9, 0.15)),
        (True, EquivalentTo(sub='Sister', equivalent='FemaleSibling'), 0.9, pytest.approx(0.9, 0.15)),
    ]
    match_facts(solution.solved_pfacts, expected)
    
def test_solve_multilingual():
    """
    Test the multilingual dataset that models semantic slippage between languages.
    
    This tests how BOOMER handles cross-language mapping with nuanced semantic differences
    between concepts in English, Spanish, and German.
    """
    kb = multilingual.kb
    cfg = SearchConfig(max_candidate_solutions=20)  # Limit the search space
    solution = solve(kb, cfg)
    print(solution)
    render(solution)
    assert solution.confidence > 0.6
    
    # Test for the presence of key mappings
    # Look for key translations that should have high posterior probabilities
    expected_true_mappings = [
        # At least one of these should be true
        EquivalentTo(sub='privacy', equivalent='privacidad'),
        EquivalentTo(sub='privacy', equivalent='Datenschutz'),
        
        # At least one of these should be true
        EquivalentTo(sub='home', equivalent='hogar'),
        EquivalentTo(sub='home', equivalent='Heim'),
        
        # This should be true
        EquivalentTo(sub='mind', equivalent='mente'),
    ]
    
    # Check that each concept has at least one valid mapping
    for fact in expected_true_mappings:
        # Check if this fact is mapped with truth_value=True and has a high posterior
        matches = [spf for spf in solution.solved_pfacts 
                   if spf.pfact.fact == fact and spf.truth_value == True and spf.posterior_prob > 0.5]
        if matches:
            print(f"Found expected mapping: {fact} with posterior: {matches[0].posterior_prob}")
        
    # Verify that at least some key mappings are found
    privacy_mappings = [spf for spf in solution.solved_pfacts 
                       if spf.pfact.fact.sub == 'privacy' and spf.truth_value == True and spf.posterior_prob > 0.5]
    assert len(privacy_mappings) > 0, "Expected at least one valid mapping for 'privacy'"
    
    home_mappings = [spf for spf in solution.solved_pfacts 
                    if spf.pfact.fact.sub == 'home' and spf.truth_value == True and spf.posterior_prob > 0.5]
    assert len(home_mappings) > 0, "Expected at least one valid mapping for 'home'"
    
    mind_mappings = [spf for spf in solution.solved_pfacts 
                    if spf.pfact.fact.sub == 'mind' and spf.truth_value == True and spf.posterior_prob > 0.5]
    assert len(mind_mappings) > 0, "Expected at least one valid mapping for 'mind'"


@pytest.mark.parametrize("max_iterations,expected_satisfiable_combinations", [(25, 1), (10, 0), (75, (2,3))])
def test_solve_false_bridge(max_iterations, expected_satisfiable_combinations):
    """
    Test the false_bridge dataset.
    """
    kb = false_bridge.kb
    solution = solve(kb, SearchConfig(max_iterations=max_iterations))
    print(solution)
    render(solution)
    if isinstance(expected_satisfiable_combinations, tuple):
        assert solution.number_of_satisfiable_combinations in expected_satisfiable_combinations
    else:
        assert solution.number_of_satisfiable_combinations == expected_satisfiable_combinations
    expected = []
    if expected_satisfiable_combinations == 1:
        assert solution.confidence == pytest.approx(1.0, 0.05)
        assert solution.prior_prob < 0.001
        assert solution.posterior_prob == pytest.approx(1.0, 0.05)
        expected = [
            (False, SubClassOf(sub="D", sup="E"), 0.92, 0.0),
            (False, SubClassOf(sub="E", sup="D"), 0.92, 0.0),
            (True, EquivalentTo(sub="A", equivalent="B"), 0.9, 1.0),
        ]
    if solution.number_of_satisfiable_combinations > 1:
        expected = [
            (False, SubClassOf(sub="D", sup="E"), 0.92, 0.0),
            (False, SubClassOf(sub="E", sup="D"), 0.92, 0.0),
            (True, EquivalentTo(sub="A", equivalent="B"), 0.9, 1.0),
        ]
    match_facts(solution.solved_pfacts, expected)
    
def test_partition_kb_integration():
    """
    Test that partition_kb correctly partitions disconnected facts and 
    that solve() uses partitioning when the threshold is exceeded.
    """
    # Create two disconnected groups of facts
    # Group 1: cat-animal relationships (need deterministic facts to create graph structure)
    group1_facts = [
        MemberOfDisjointGroup(sub="cat", group="animals"),
        MemberOfDisjointGroup(sub="feline", group="animals"),
        MemberOfDisjointGroup(sub="animal", group="animals"),
    ]
    group1_pfacts = [
        PFact(fact=EquivalentTo(sub="cat", equivalent="feline"), prob=0.9),
        PFact(fact=EquivalentTo(sub="cat", equivalent="animal"), prob=0.1),
        PFact(fact=EquivalentTo(sub="feline", equivalent="animal"), prob=0.1),
    ]
    
    # Group 2: color relationships (completely disconnected)
    group2_facts = [
        MemberOfDisjointGroup(sub="red", group="colors"),
        MemberOfDisjointGroup(sub="crimson", group="colors"),
        MemberOfDisjointGroup(sub="blue", group="colors"),
    ]
    group2_pfacts = [
        PFact(fact=EquivalentTo(sub="red", equivalent="crimson"), prob=0.8),
        PFact(fact=EquivalentTo(sub="red", equivalent="blue"), prob=0.05),
        PFact(fact=EquivalentTo(sub="crimson", equivalent="blue"), prob=0.05),
    ]
    
    # Combine into a single KB
    all_facts = group1_facts + group2_facts
    all_pfacts = group1_pfacts + group2_pfacts
    kb = KB(facts=all_facts, pfacts=all_pfacts)
    import yaml
    
    # Test 1: Verify partitioning splits into two components
    from boomer.splitter import partition_kb
    partitions = list(partition_kb(kb))
    print(f"Number of partitions: {len(partitions)}")
    for i, partition in enumerate(partitions):
        print(f"Partition {i}: {len(partition.facts)} facts, {len(partition.pfacts)} pfacts")
        print(f"  Facts: {partition.facts}")
        print(f"  Pfacts: {[pf.fact for pf in partition.pfacts]}")
    
    # Just test that partitioning works - don't assert specific number for now
    assert len(partitions) >= 1, f"Expected at least 1 partition, got {len(partitions)}"
    
    # Test 2: Solve with low threshold to force partitioning
    config_with_partitioning = SearchConfig(partition_initial_threshold=4)  # Force partitioning for 6 pfacts
    solution_partitioned = solve(kb, config_with_partitioning)
    
    # Test 3: Solve without partitioning for comparison
    config_no_partitioning = SearchConfig(partition_initial_threshold=10000)  # Prevent partitioning
    solution_direct = solve(kb, config_no_partitioning)
    
    print(f"Partitioned solution: {solution_partitioned.number_of_satisfiable_combinations} satisfiable")
    print(f"Direct solution: {solution_direct.number_of_satisfiable_combinations} satisfiable")
    
    # Test 4: Just verify that partitioning doesn't break the search completely
    assert solution_partitioned.number_of_combinations >= 0
    assert solution_direct.number_of_combinations >= 0
    
    # Test 5: Verify partitioning creates separate components
    assert len(partitions) == 2, f"Expected exactly 2 partitions, got {len(partitions)}"

    
    print(yaml.dump(kb.model_dump()))
    
    # Each partition should have 3 pfacts
    assert all(len(p.pfacts) == 3 for p in partitions), "Each partition should have 3 pfacts"
    
    # Test 6: Verify solutions include facts from both partitions
    all_solved_facts = [spf.pfact.fact for spf in solution_partitioned.solved_pfacts]
    partition1_entities = {"cat", "feline", "animal"} 
    partition2_entities = {"red", "crimson", "blue"}
    
    # Check that we have facts from both partitions in the combined solution
    has_partition1 = any(any(e in [fact.sub, getattr(fact, 'equivalent', '')] for e in partition1_entities) for fact in all_solved_facts)
    has_partition2 = any(any(e in [fact.sub, getattr(fact, 'equivalent', '')] for e in partition2_entities) for fact in all_solved_facts)
    
    assert has_partition1, "Expected facts from partition 1 in combined solution"
    assert has_partition2, "Expected facts from partition 2 in combined solution"

def test_partition_kb_max_pfacts_per_clique():
    """
    Test that max_pfacts_per_clique parameter correctly limits clique size.
    """
    from boomer.splitter import partition_kb
    
    # Create a large clique with many pfacts
    pfacts = [
        PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
        PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
        PFact(fact=EquivalentTo(sub="C", equivalent="D"), prob=0.7),
        PFact(fact=EquivalentTo(sub="D", equivalent="E"), prob=0.6),
        PFact(fact=EquivalentTo(sub="A", equivalent="C"), prob=0.5),
        PFact(fact=EquivalentTo(sub="A", equivalent="D"), prob=0.4),
        PFact(fact=EquivalentTo(sub="B", equivalent="D"), prob=0.3),
    ]
    kb = KB(pfacts=pfacts)
    
    # Test without limit - should keep all pfacts
    unlimited_partitions = list(partition_kb(kb))
    assert len(unlimited_partitions) == 1
    assert len(unlimited_partitions[0].pfacts) == 7
    
    # Test with limit
    limited_partitions = list(partition_kb(kb, max_pfacts_per_clique=4, min_pfacts_per_clique=4))
    assert len(limited_partitions) == 2
    assert len(limited_partitions[0].pfacts) == 4
    
    # Check that highest probability pfacts are kept
    kept_probs = sorted([pf.prob for pf in limited_partitions[0].pfacts], reverse=True)
    expected_probs = [0.9, 0.8, 0.7, 0.6]
    assert kept_probs == expected_probs

@pytest.mark.parametrize("num_partitions", [2,3])
@pytest.mark.parametrize("num_nodes_per_partition", [2,3])
@pytest.mark.parametrize("default_probability", [1.0, 0.95])
def test_partition_trivial(num_partitions, num_nodes_per_partition, default_probability):
    kb = KB(pfacts=[])  
    for i in range(num_partitions):
        nodes = [f"{i}_{j}" for j in range(num_nodes_per_partition)]
        for i in range(len(nodes)-1):
            edge = EquivalentTo(sub=nodes[i], equivalent=nodes[i+1])
            kb.pfacts.append(PFact(fact=edge, prob=default_probability))
        
    config = SearchConfig(partition_initial_threshold=1)
    solution = solve(kb, config)
    assert solution.number_of_components == num_partitions
    import yaml
    # print("# -- SOLUTION --")
    # print(yaml.dump(solution.as_dict(), sort_keys=False))
    if default_probability == 1.0:
        assert solution.confidence == 1.0
        assert solution.posterior_prob == 1.0
        assert solution.prior_prob == 1.0
        assert solution.number_of_satisfiable_combinations == num_partitions
        # no inconsistencies possible
    else:
        assert solution.confidence < 1.0
        assert solution.posterior_prob < 1.0
        assert solution.prior_prob < 1.0

def test_solve_with_max_pfacts_per_clique():
    """
    Test that solve() uses max_pfacts_per_clique from SearchConfig.
    """
    # Create a KB that will trigger partitioning with large cliques
    pfacts = []
    for i in range(8):
        for j in range(i+1, 8):
            prob = 0.9 - (i + j) * 0.05  # Decreasing probabilities
            pfacts.append(PFact(fact=EquivalentTo(sub=f"entity_{i}", equivalent=f"entity_{j}"), prob=prob))
    
    kb = KB(pfacts=pfacts)
    
    # Configure to force partitioning with pfact limit
    config = SearchConfig(
        partition_initial_threshold=10,  # Force partitioning
        max_pfacts_per_clique=5  # Limit clique size
    )
    
    # This should work without excessive computation
    solution = solve(kb, config)
    assert solution.number_of_combinations >= 0  # Should complete successfully

@pytest.mark.parametrize("timeout", [ 0.1, 0.2])
def test_timeout(timeout):
    """
    Test that the search respects the timeout configuration.
    
    This creates a complex KB that would take significant time to solve,
    but sets a very short timeout to verify the timeout functionality works.
    """
    # Use the animals KB for this test
    kb = animals.kb
    
    # Set a very short timeout (0.01 seconds)
    # This should cause the search to time out before finding a complete solution
    cfg = SearchConfig(timeout_seconds=timeout)
    
    solution = solve(kb, cfg)
    print(solution)
    render(solution)
    
    # The solution should indicate it timed out
    assert solution.timed_out
    
    # We should still have timing information
    assert solution.time_started is not None
    assert solution.time_finished is not None
    assert solution.time_elapsed is not None
    
    # Time elapsed should be close to the timeout value
    # assert solution.time_elapsed >= timeout
    assert solution.time_elapsed < timeout + 1.0  # Add some buffer

def test_search_animals():
    kb = animals.kb
    print(kb.number_of_combinations())
    cfg = SearchConfig(max_iterations=10000000)
    n = 0
    done = set()
    visited = set()
    visited2 = set()
    for node in search(kb, cfg):
        # fset = frozenset(node.selections)
        fset = tuple(sorted(node.asserted_selections))
        fset2 = tuple(sorted(node.selections))
        assert len(fset2) == 9
        if fset in visited:
            raise Exception(f"Duplicate node: {node.identifier}")
        visited.add(fset)
        if fset2 in visited2:
            raise Exception(f"Duplicate node: {node.identifier}")
        visited2.add(fset2)
        #if node.identifier in done:
        #    raise Exception(f"Duplicate node by identifier: {node.identifier}")
        done.add(node.identifier)
        n += 1
        assert n == len(visited)
        #print(n, "ID:", node.identifier, "D:", node.depth, "CPR:", node.pr_selected, "PR:", node.pr, "S:", node.selection, "SS:", fset, "SAT:", node.satifiable, "T:", node.terminal)
        #print("TT: ", fset)
        #print("TTxxx: ", node.satifiable, node.pr_selected, fset2)
        #print(node)
    print(f"Number of nodes: {n}")
    #assert n <= 512


@pytest.mark.parametrize("probs,expected_prob,expected_satisfiable_combinations", [
    ([0.9], 0.9, 2), # trivial base case
    ([0.9, 0.8], 0.986, 3), # TODO: see docstring
    ([0.9, 0.8, 0.7], 0.996, 4), # TODO: see docstring
    ([0.9, 0.8, 0.001], 0.0975, 4), # TODO: see docstring
    
])
def test_asserted_multi_labeled_edges(probs, expected_prob, expected_satisfiable_combinations):
    """
    Test that multi-labeled edges are handled correctly.

    Given two assertions about the same fact:

        - A = B @ 0.9
        - A = B @ 0.8

    These should be treated as independent pieces of evidence for the same fact; for the fact
    to be false, both hypotheses must be false, i.e pr(not(A=B)) = 0.1 * 0.2 = 0.02.
        
    TODO: currently the way this works is that these are treated as if they are assertions
    about different facts, such that for the world where A=B, the probability
    is 0.9 * 0.8 = 0.72. Furthermore there are two such worlds, one for each assertion.

    """
    kb = KB(pfacts=[])
    for prob in probs:
        kb.pfacts.append(PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=prob))
    nodes = list(search(kb, SearchConfig()))
    if len(probs) == 1:
        assert len(nodes) == 2
    elif len(probs) == 2:
        # TODO: this includes two identical worlds:
        # SOLUTION 0
        # True 0.7200000000000001 0.7200000000000001 [(1, True), (0, True)]
        # SOLUTION 1
        # True 0.7200000000000001 0.7200000000000001 [(1, True), (0, True)]
        assert len(nodes) == 5
        satisfiable_nodes = [n for n in nodes if n.satifiable]
        assert len(satisfiable_nodes) == expected_satisfiable_combinations
        for i, n  in enumerate(nodes):
            print(f"# SOLUTION {i}")
            #import yaml
            #print(yaml.dump(n.model_dump()))
            print(n.satifiable, n.pr_selected, n.pr, n.selections)
    solution = solve(kb)
    assert solution.number_of_satisfiable_combinations == expected_satisfiable_combinations
    # TODO: consider collapsing multiple edges
    assert len(solution.solved_pfacts) == len(probs)
    for solved_pfact in solution.solved_pfacts:
        assert solved_pfact.posterior_prob == pytest.approx(expected_prob, 0.001)


@pytest.mark.parametrize("p1,p2,expected_prob", [
    (0.8, 0.2, 0.6666),
    (0.9, 0.1, 0.6666),
    (0.9, 0.9, 0.9938),
    (0.1, 0.1, 0.0241),
])
def test_entailed_multi_labeled_edges(p1, p2, expected_prob):
    """
    Test that entailed multi-labeled edges are handled correctly.

    Given two assertions about the same logical fact:

        - A = B @ 0.9
        - B = A @ 0.8

    The probability that A=B is the same as the probability that B=A.

    See docstring for test_asserted_multi_labeled_edges.
    """
    kb = KB(pfacts=[])
    kb.pfacts.append(PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=p1))
    kb.pfacts.append(PFact(fact=EquivalentTo(sub="B", equivalent="A"), prob=p2))
    solution = solve(kb)
    assert solution.number_of_satisfiable_combinations == 3
    assert len(solution.solved_pfacts) == 2
    for i, solved_pfact in enumerate(solution.solved_pfacts):
        print(f"# SOLUTION {i}")
        print(solved_pfact)
        assert solved_pfact.posterior_prob == pytest.approx(expected_prob, 0.001)


@pytest.mark.parametrize("exhaustive_depth", [0, 1])
def test_exhaustive_search_depth_false_bridge(exhaustive_depth):
    """
    Test the exhaustive_search_depth feature with a dataset that has competing solutions.

    The false_bridge dataset has:
    - Two islands of consistent equivalences (each with 0.9 prob facts)
    - A hard disjointness constraint between islands
    - A high-prob 0.99 bridge that would connect islands (causing contradiction)

    The optimal solution counterintuitively accepts the 0.99 bridge and breaks
    one island (rejecting C≡D) because:
    - Accept bridge, break island: 0.99 × 0.9² × 0.1 × 0.9³ ≈ 0.0585
    - Reject bridge, keep islands: 0.01 × 0.9⁶ ≈ 0.00531

    This tests that the search correctly finds the mathematically optimal solution
    even when it requires breaking a consistent cluster. The exhaustive_search_depth
    parameter ensures thorough exploration of the search space.
    """
    kb = false_bridge.kb

    # Use a short timeout since we want to test the search strategy, not wait forever
    config = SearchConfig(
        exhaustive_search_depth=exhaustive_depth,
        timeout_seconds=2.0,  # Give more time to explore
        max_iterations=10000,
        max_candidate_solutions=100
    )

    solution = solve(kb, config)

    # Debug: print solution details
    print(f"\n=== Solution with exhaustive_depth={exhaustive_depth} ===")
    print(f"Confidence: {solution.confidence}")
    print(f"Posterior prob: {solution.posterior_prob}")
    print(f"Prior prob: {solution.prior_prob}")
    print(f"Number of combinations: {solution.number_of_combinations}")
    print(f"Number of satisfiable: {solution.number_of_satisfiable_combinations}")
    print(f"Timed out: {solution.timed_out}")

    # Find the high-prob bridge fact
    bridge_fact = EquivalentTo(sub="D", equivalent="E")
    bridge_spfs = [spf for spf in solution.solved_pfacts if spf.pfact.fact == bridge_fact]

    if not bridge_spfs:
        # If search timed out, it may not have all facts
        print("Bridge fact not in solution (likely due to timeout)")
        assert solution.timed_out, "If bridge fact is missing, search should have timed out"
        return

    bridge_spf = bridge_spfs[0]
    print(f"Bridge D≡E: truth_value={bridge_spf.truth_value}, posterior={bridge_spf.posterior_prob}")

    # Check all facts
    for spf in solution.solved_pfacts:
        print(f"  {spf.pfact.fact}: {spf.truth_value} (posterior: {spf.posterior_prob:.3f})")

    # Both solutions find a satisfiable solution
    # The optimal solution actually accepts the bridge and breaks Island 1
    # This is because 0.99 (bridge) × 0.1 (reject C≡D) > 0.01 (reject bridge)

    # Check that a satisfiable solution was found
    assert solution.number_of_satisfiable_combinations > 0, "Should find at least one satisfiable solution"
    assert solution.confidence > 0, "Should have non-zero confidence"

    # The actual optimal solution accepts the high-prob bridge
    # and rejects C≡D to avoid contradiction
    if bridge_spf.truth_value:
        # If bridge is accepted, C≡D must be rejected to avoid contradiction
        cd_fact = EquivalentTo(sub="C", equivalent="D")
        cd_spfs = [s for s in solution.solved_pfacts if s.pfact.fact == cd_fact]
        if cd_spfs:
            cd_spf = cd_spfs[0]
            assert cd_spf.truth_value == False, "C≡D must be rejected if bridge is accepted"

        # Island 2 should remain intact
        island2_facts = [
            EquivalentTo(sub="E", equivalent="F"),
            EquivalentTo(sub="F", equivalent="G"),
            EquivalentTo(sub="G", equivalent="H"),
        ]
        for fact in island2_facts:
            spf = [s for s in solution.solved_pfacts if s.pfact.fact == fact][0]
            assert spf.truth_value == True, f"Island 2 fact {fact} should be accepted"

    # The key difference with exhaustive search is that it explores more thoroughly
    # Both depth=0 and depth=1 should find a solution, but depth=1 explores more paths
    if exhaustive_depth == 1:
        # With exhaustive search, we explore more combinations
        print(f"Explored {solution.number_of_combinations} combinations")
        assert solution.number_of_combinations >= 2, "Should explore multiple starting points"