import pytest
import tempfile
import json
from boomer.io import (
    ptable_to_kb, ptable_to_pfacts, id_prefix,
    kb_to_json, kb_from_json, kb_to_yaml, kb_from_yaml,
    save_kb, load_kb
)
from boomer.model import PFact, ProperSubClassOf, EquivalentTo, NotInSubsumptionWith, MemberOfDisjointGroup, KB, Solution, SolvedPFact
from boomer.renderers.markdown_renderer import MarkdownRenderer
from boomer.search import solve
from pathlib import Path
import os

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

def get_test_file_path(filename):
    """Get the absolute path to a test file"""
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(current_dir, "input", filename)

def test_id_prefix():
    """Test the id_prefix function for extracting prefixes from IDs."""
    assert id_prefix("MONDO:0000023") == "MONDO"
    assert id_prefix("ORDO:464724") == "ORDO"
    assert id_prefix("ICD10CM:K72.0") == "ICD10CM"
    
    # Test error handling for invalid IDs
    with pytest.raises(ValueError):
        id_prefix("invalid_id")

def test_ptable_to_kb():
    """Test parsing of probability table files to KB."""
    file_path = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    # Convert file to KB
    kb = ptable_to_kb(file_path)
    
    # Verify KB has a name derived from the file
    assert kb.name == "MONDO_0000023.ptable"
    
    # Verify the correct number of facts and pfacts
    # Count the actual unique IDs
    unique_ids = set()
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    unique_ids.add(parts[0])
                    unique_ids.add(parts[1])
    
    # Each row generates 4 pfacts
    expected_pfact_count = 7 * 3
    assert len(kb.pfacts) == expected_pfact_count
    
    # Each unique ID generates a disjoint group fact
    expected_fact_count = len(unique_ids)
    assert len(kb.facts) == expected_fact_count
    
    # Check a few specific facts to ensure they're parsed correctly
    # First row: ORDO:464724  MONDO:0000023 0.033333333333333326 0.033333333333333326 0.9 0.033333333333333326
    
    # ProperSubClassOf(ORDO:464724, MONDO:0000023) with prob=0.033...
    sub_fact = next((pf for pf in kb.pfacts if isinstance(pf.fact, ProperSubClassOf) 
                    and pf.fact.sub == "ORDO:464724" and pf.fact.sup == "MONDO:0000023"), None)
    assert sub_fact is not None
    assert sub_fact.prob == pytest.approx(0.033333333333333326)
    
    # EquivalentTo(ORDO:464724, MONDO:0000023) with prob=0.9
    equiv_fact = next((pf for pf in kb.pfacts if isinstance(pf.fact, EquivalentTo) 
                      and pf.fact.sub == "ORDO:464724" and pf.fact.equivalent == "MONDO:0000023"), None)
    assert equiv_fact is not None
    assert equiv_fact.prob == pytest.approx(0.9)
    
    # Verify disjoint group memberships are created as facts
    mondo_group = next((f for f in kb.facts if isinstance(f, MemberOfDisjointGroup) 
                      and f.sub == "MONDO:0000023" and f.group == "MONDO"), None)
    assert mondo_group is not None

def test_ptable_to_pfacts_backward_compatibility():
    """Test backward compatibility of ptable_to_pfacts."""
    file_path = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    # Convert file to PFacts
    pfacts = list(ptable_to_pfacts(file_path))
    
    # Verify we got the expected number of PFacts
    # Each row generates 4 relationship PFacts, plus each unique ID generates a disjoint group fact
    # Let's count the actual unique IDs
    unique_ids = set()
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    unique_ids.add(parts[0])
                    unique_ids.add(parts[1])
    
    expected_pfact_count = (7 * 3) + len(unique_ids)
    assert len(pfacts) == expected_pfact_count

def test_ptable_search():
    """Test creating a KB from a probability table and solving it."""
    file_path = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    # Create KB directly from the ptable file
    kb = ptable_to_kb(file_path, description="Acute liver failure")
    
    # Solve the KB with limited search space to ensure test completes quickly
    from boomer.model import SearchConfig
    cfg = SearchConfig(max_candidate_solutions=50)
    solution = solve(kb, cfg)
    print(solution)
    renderer = MarkdownRenderer()
    print(renderer.render(solution))
    
    # Verify the solution has valid fields
    assert solution.confidence > 0
    assert solution.number_of_satisfiable_combinations > 0
    assert solution.time_elapsed is not None
    
    # Verify some of the key expected mappings in the solution
    # We expect MONDO:0024568 and MONDO:0000023 to be equivalent (prob 1.0 in the input)
    mondo_equiv_facts = [spf for spf in solution.solved_pfacts 
                        if isinstance(spf.pfact.fact, EquivalentTo) 
                        and spf.pfact.fact.sub == "MONDO:0024568" 
                        and spf.pfact.fact.equivalent == "MONDO:0000023"]
    
    # We should have at least one such fact (either true or false)
    assert len(mondo_equiv_facts) > 0
    
    # Check other key relationships present in the input data
    ordo_mondo_facts = [spf for spf in solution.solved_pfacts 
                       if isinstance(spf.pfact.fact, EquivalentTo) 
                       and spf.pfact.fact.sub == "ORDO:464724" 
                       and spf.pfact.fact.equivalent == "MONDO:0000023"]
    assert len(ordo_mondo_facts) > 0


# JSON serialization tests

def test_kb_to_json():
    """Test KB serialization to JSON."""
    # Create a simple KB for testing
    kb = KB(
        name="test_kb",
        description="A test knowledge base",
        facts=[MemberOfDisjointGroup(sub="cat", group="animals")],
        pfacts=[
            PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            PFact(fact=EquivalentTo(sub="cat", equivalent="feline"), prob=0.8)
        ]
    )
    
    # Serialize to JSON
    json_str = kb_to_json(kb)
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed["name"] == "test_kb"
    assert parsed["description"] == "A test knowledge base"
    assert len(parsed["facts"]) == 1
    assert len(parsed["pfacts"]) == 2
    
    # Verify the structure includes all necessary fields
    assert "facts" in parsed
    assert "pfacts" in parsed
    assert "hypotheses" in parsed
    assert "labels" in parsed


def test_kb_from_json():
    """Test KB deserialization from JSON."""
    # Create test JSON
    json_data = {
        "name": "test_kb",
        "description": "A test knowledge base",
        "comments": None,
        "facts": [
            {
                "fact_type": "MemberOfDisjointGroup",
                "sub": "cat",
                "group": "animals"
            }
        ],
        "pfacts": [
            {
                "fact": {
                    "fact_type": "ProperSubClassOf",
                    "sub": "cat",
                    "sup": "animal"
                },
                "prob": 0.9
            }
        ],
        "hypotheses": [],
        "labels": {}
    }
    
    json_str = json.dumps(json_data)
    
    # Deserialize from JSON
    kb = kb_from_json(json_str)
    
    # Verify the KB structure
    assert kb.name == "test_kb"
    assert kb.description == "A test knowledge base"
    assert len(kb.facts) == 1
    assert len(kb.pfacts) == 1
    
    # Verify the fact types
    assert isinstance(kb.facts[0], MemberOfDisjointGroup)
    assert isinstance(kb.pfacts[0].fact, ProperSubClassOf)
    assert kb.pfacts[0].prob == 0.9


def test_json_roundtrip():
    """Test that JSON serialization and deserialization preserve data."""
    from boomer.datasets.animals import kb
    
    # Serialize and deserialize
    json_str = kb_to_json(kb)
    kb_restored = kb_from_json(json_str)
    
    # Verify the data is preserved
    assert kb_restored.name == kb.name
    assert kb_restored.description == kb.description
    assert len(kb_restored.facts) == len(kb.facts)
    assert len(kb_restored.pfacts) == len(kb.pfacts)
    
    # Verify specific facts are preserved
    for original_fact, restored_fact in zip(kb.facts, kb_restored.facts):
        assert type(original_fact) == type(restored_fact)
        if isinstance(original_fact, MemberOfDisjointGroup):
            assert original_fact.sub == restored_fact.sub
            assert original_fact.group == restored_fact.group
    
    for original_pfact, restored_pfact in zip(kb.pfacts, kb_restored.pfacts):
        assert type(original_pfact.fact) == type(restored_pfact.fact)
        assert original_pfact.prob == restored_pfact.prob


# YAML serialization tests

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not available")
def test_kb_to_yaml():
    """Test KB serialization to YAML."""
    # Create a simple KB for testing
    kb = KB(
        name="test_kb",
        description="A test knowledge base",
        facts=[MemberOfDisjointGroup(sub="cat", group="animals")],
        pfacts=[PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9)]
    )
    
    # Serialize to YAML
    yaml_str = kb_to_yaml(kb)
    
    # Verify it's valid YAML
    parsed = yaml.safe_load(yaml_str)
    assert parsed["name"] == "test_kb"
    assert parsed["description"] == "A test knowledge base"
    assert len(parsed["facts"]) == 1
    assert len(parsed["pfacts"]) == 1


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not available")
def test_kb_from_yaml():
    """Test KB deserialization from YAML."""
    yaml_str = """
name: test_kb
description: A test knowledge base
comments: null
facts:
- fact_type: MemberOfDisjointGroup
  sub: cat
  group: animals
pfacts:
- fact:
    fact_type: ProperSubClassOf
    sub: cat
    sup: animal
  prob: 0.9
hypotheses: []
labels: {}
"""
    
    # Deserialize from YAML
    kb = kb_from_yaml(yaml_str)
    
    # Verify the KB structure
    assert kb.name == "test_kb"
    assert kb.description == "A test knowledge base"
    assert len(kb.facts) == 1
    assert len(kb.pfacts) == 1
    assert isinstance(kb.facts[0], MemberOfDisjointGroup)
    assert isinstance(kb.pfacts[0].fact, ProperSubClassOf)
    assert kb.pfacts[0].prob == 0.9


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not available")
def test_yaml_roundtrip():
    """Test that YAML serialization and deserialization preserve data."""
    from boomer.datasets.animals import kb
    
    # Serialize and deserialize
    yaml_str = kb_to_yaml(kb)
    kb_restored = kb_from_yaml(yaml_str)
    
    # Verify the data is preserved
    assert kb_restored.name == kb.name
    assert kb_restored.description == kb.description
    assert len(kb_restored.facts) == len(kb.facts)
    assert len(kb_restored.pfacts) == len(kb.pfacts)


# File I/O tests

def test_save_load_kb_json():
    """Test saving and loading KB to/from JSON files."""
    from boomer.datasets.animals import kb
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json_file = f.name
    
    try:
        # Save to JSON file
        save_kb(kb, json_file)
        
        # Load from JSON file
        kb_loaded = load_kb(json_file)
        
        # Verify the data is preserved
        assert kb_loaded.name == kb.name
        assert len(kb_loaded.facts) == len(kb.facts)
        assert len(kb_loaded.pfacts) == len(kb.pfacts)
        
    finally:
        os.unlink(json_file)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not available")
def test_save_load_kb_yaml():
    """Test saving and loading KB to/from YAML files."""
    from boomer.datasets.animals import kb
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_file = f.name
    
    try:
        # Save to YAML file
        save_kb(kb, yaml_file)
        
        # Load from YAML file
        kb_loaded = load_kb(yaml_file)
        
        # Verify the data is preserved
        assert kb_loaded.name == kb.name
        assert len(kb_loaded.facts) == len(kb.facts)
        assert len(kb_loaded.pfacts) == len(kb.pfacts)
        
    finally:
        os.unlink(yaml_file)


def test_auto_format_detection():
    """Test automatic format detection based on file extension."""
    from boomer.datasets.animals import kb
    
    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = os.path.join(tmpdir, "test.json")
        yaml_file = os.path.join(tmpdir, "test.yaml")
        yml_file = os.path.join(tmpdir, "test.yml")
        
        # Test auto-detection for saving
        save_kb(kb, json_file, format="auto")
        save_kb(kb, yaml_file, format="auto") if YAML_AVAILABLE else None
        save_kb(kb, yml_file, format="auto") if YAML_AVAILABLE else None
        
        # Test auto-detection for loading
        kb_json = load_kb(json_file, format="auto")
        assert kb_json.name == kb.name
        
        if YAML_AVAILABLE:
            kb_yaml = load_kb(yaml_file, format="auto")
            assert kb_yaml.name == kb.name
            
            kb_yml = load_kb(yml_file, format="auto")
            assert kb_yml.name == kb.name


def test_error_handling():
    """Test error handling for invalid inputs."""
    # Test invalid JSON
    with pytest.raises(ValueError, match="Failed to parse KB from JSON"):
        kb_from_json("invalid json")
    
    # Test invalid YAML (if available)
    if YAML_AVAILABLE:
        with pytest.raises(ValueError, match="Failed to parse KB from YAML"):
            kb_from_yaml("invalid: yaml: [")
    
    # Test unsupported format
    with pytest.raises(ValueError, match="Unsupported format"):
        save_kb(KB(), "test.txt", format="txt")
    
    # Test file not found
    with pytest.raises(FileNotFoundError):
        load_kb("nonexistent_file.json")
    
    # Test unsupported extension for auto-detection
    with pytest.raises(ValueError, match="Cannot auto-detect format"):
        save_kb(KB(), "test.unknown", format="auto")


# Tests for label inclusion in renderers

def test_tsv_renderer_with_labels():
    """Test TSV renderer includes labels when KB has labels."""
    from boomer.renderers.tsv_renderer import TSVRenderer
    
    # Create a KB with labels
    kb_with_labels = KB(
        name="test_kb_with_labels",
        facts=[MemberOfDisjointGroup(sub="cat", group="animals")],
        pfacts=[
            PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            PFact(fact=EquivalentTo(sub="cat", equivalent="feline"), prob=0.8)
        ],
        labels={
            "cat": "Domestic Cat",
            "animal": "Animal",
            "feline": "Feline"
        }
    )
    
    # Create mock solution
    solved_pfacts = [
        SolvedPFact(
            pfact=PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            truth_value=True,
            posterior_prob=0.95
        ),
        SolvedPFact(
            pfact=PFact(fact=EquivalentTo(sub="cat", equivalent="feline"), prob=0.8),
            truth_value=True,
            posterior_prob=0.85
        )
    ]
    
    mock_solution = Solution(
        ground_pfacts=[],
        solved_pfacts=solved_pfacts,
        number_of_combinations=4,
        number_of_satisfiable_combinations=3,
        number_of_combinations_explored_including_implicit=4,
        confidence=0.9,
        prior_prob=0.1,
        posterior_prob=0.8,
        proportion_of_combinations_explored=1.0
    )
    
    # Test TSV renderer with labels
    renderer = TSVRenderer()
    output = renderer.render(mock_solution, kb_with_labels)
    
    # Verify label columns are present
    lines = output.strip().split('\n')
    header_line = None
    for line in lines:
        if line.startswith('fact_type'):
            header_line = line
            break
    
    assert header_line is not None
    headers = header_line.split('\t')
    
    # Should have label columns
    assert 'arg1_label' in headers
    assert 'arg2_label' in headers
    
    # Check that labels are included in the data
    assert "Domestic Cat" in output
    assert "Animal" in output
    assert "Feline" in output


def test_tsv_renderer_without_labels():
    """Test TSV renderer works correctly when KB has no labels."""
    from boomer.renderers.tsv_renderer import TSVRenderer
    
    # Create a KB without labels
    kb_without_labels = KB(
        name="test_kb_no_labels",
        facts=[MemberOfDisjointGroup(sub="cat", group="animals")],
        pfacts=[PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9)]
    )
    
    # Create mock solution
    solved_pfacts = [
        SolvedPFact(
            pfact=PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            truth_value=True,
            posterior_prob=0.95
        )
    ]
    
    mock_solution = Solution(
        ground_pfacts=[],
        solved_pfacts=solved_pfacts,
        number_of_combinations=2,
        number_of_satisfiable_combinations=1,
        number_of_combinations_explored_including_implicit=2,
        confidence=0.95,
        prior_prob=0.1,
        posterior_prob=0.9,
        proportion_of_combinations_explored=1.0
    )
    
    # Test TSV renderer without labels
    renderer = TSVRenderer()
    output = renderer.render(mock_solution, kb_without_labels)
    
    # Verify no label columns are present
    lines = output.strip().split('\n')
    header_line = None
    for line in lines:
        if line.startswith('fact_type'):
            header_line = line
            break
    
    assert header_line is not None
    headers = header_line.split('\t')
    
    # Should NOT have label columns
    assert 'arg1_label' not in headers
    assert 'arg2_label' not in headers


def test_tsv_renderer_no_kb():
    """Test TSV renderer works when no KB is provided."""
    from boomer.renderers.tsv_renderer import TSVRenderer
    
    # Create mock solution
    solved_pfacts = [
        SolvedPFact(
            pfact=PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            truth_value=True,
            posterior_prob=0.95
        )
    ]
    
    mock_solution = Solution(
        ground_pfacts=[],
        solved_pfacts=solved_pfacts,
        number_of_combinations=2,
        number_of_satisfiable_combinations=1,
        number_of_combinations_explored_including_implicit=2,
        confidence=0.95,
        prior_prob=0.1,
        posterior_prob=0.9,
        proportion_of_combinations_explored=1.0
    )
    
    # Test TSV renderer with no KB
    renderer = TSVRenderer()
    output = renderer.render(mock_solution)  # No KB provided
    
    # Should still work and not have label columns
    lines = output.strip().split('\n')
    header_line = None
    for line in lines:
        if line.startswith('fact_type'):
            header_line = line
            break
    
    assert header_line is not None
    headers = header_line.split('\t')
    assert 'arg1_label' not in headers


def test_markdown_renderer_with_labels():
    """Test Markdown renderer includes labels when KB has labels."""
    from boomer.renderers.markdown_renderer import MarkdownRenderer
    
    # Create a KB with labels
    kb_with_labels = KB(
        name="test_kb_with_labels",
        facts=[MemberOfDisjointGroup(sub="cat", group="animals")],
        pfacts=[
            PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            PFact(fact=EquivalentTo(sub="dog", equivalent="canine"), prob=0.8)
        ],
        labels={
            "cat": "Domestic Cat",
            "animal": "Animal",
            "dog": "Domestic Dog",
            "canine": "Canine"
        }
    )
    
    # Create mock solution
    solved_pfacts = [
        SolvedPFact(
            pfact=PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            truth_value=True,
            posterior_prob=0.95
        ),
        SolvedPFact(
            pfact=PFact(fact=EquivalentTo(sub="dog", equivalent="canine"), prob=0.8),
            truth_value=True,
            posterior_prob=0.85
        )
    ]
    
    mock_solution = Solution(
        ground_pfacts=[],
        solved_pfacts=solved_pfacts,
        number_of_combinations=4,
        number_of_satisfiable_combinations=3,
        number_of_combinations_explored_including_implicit=4,
        confidence=0.9,
        prior_prob=0.1,
        posterior_prob=0.8,
        proportion_of_combinations_explored=1.0
    )
    
    # Test Markdown renderer with labels
    renderer = MarkdownRenderer()
    output = renderer.render(mock_solution, kb_with_labels)
    
    # Verify labels are included in the output
    assert "cat (Domestic Cat)" in output
    assert "animal (Animal)" in output
    assert "dog (Domestic Dog)" in output
    assert "canine (Canine)" in output
    
    # Verify proper symbols are used
    assert "⊆" in output  # SubClassOf symbol
    assert "≡" in output  # EquivalentTo symbol


def test_markdown_renderer_without_labels():
    """Test Markdown renderer works correctly when KB has no labels."""
    from boomer.renderers.markdown_renderer import MarkdownRenderer
    
    # Create a KB without labels
    kb_without_labels = KB(
        name="test_kb_no_labels",
        facts=[MemberOfDisjointGroup(sub="cat", group="animals")],
        pfacts=[PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9)]
    )
    
    # Create mock solution
    solved_pfacts = [
        SolvedPFact(
            pfact=PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            truth_value=True,
            posterior_prob=0.95
        )
    ]
    
    mock_solution = Solution(
        ground_pfacts=[],
        solved_pfacts=solved_pfacts,
        number_of_combinations=2,
        number_of_satisfiable_combinations=1,
        number_of_combinations_explored_including_implicit=2,
        confidence=0.95,
        prior_prob=0.1,
        posterior_prob=0.9,
        proportion_of_combinations_explored=1.0
    )
    
    # Test Markdown renderer without labels
    renderer = MarkdownRenderer()
    output = renderer.render(mock_solution, kb_without_labels)
    
    # Should still work and just show the original fact representation
    assert "cat" in output
    assert "animal" in output
    # Should not have label parentheses
    assert "(" not in output or "posterior:" in output  # Only allow posterior: parentheses


def test_markdown_renderer_no_kb():
    """Test Markdown renderer works when no KB is provided."""
    from boomer.renderers.markdown_renderer import MarkdownRenderer
    
    # Create mock solution
    solved_pfacts = [
        SolvedPFact(
            pfact=PFact(fact=ProperSubClassOf(sub="cat", sup="animal"), prob=0.9),
            truth_value=True,
            posterior_prob=0.95
        )
    ]
    
    mock_solution = Solution(
        ground_pfacts=[],
        solved_pfacts=solved_pfacts,
        number_of_combinations=2,
        number_of_satisfiable_combinations=1,
        number_of_combinations_explored_including_implicit=2,
        confidence=0.95,
        prior_prob=0.1,
        posterior_prob=0.9,
        proportion_of_combinations_explored=1.0
    )
    
    # Test Markdown renderer with no KB
    renderer = MarkdownRenderer()
    output = renderer.render(mock_solution)  # No KB provided
    
    # Should still work
    assert "cat" in output
    assert "animal" in output