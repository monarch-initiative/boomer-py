import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from boomer.cli import cli, get_renderer, load_kb
from boomer.model import KB, SolvedPFact, PFact, EquivalentTo
from boomer.renderers.markdown_renderer import MarkdownRenderer


def get_test_file_path(filename):
    """Get the absolute path to a test file"""
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(current_dir, "input", filename)


def test_get_renderer():
    """Test that the correct renderer is returned."""
    from boomer.renderers.tsv_renderer import TSVRenderer
    from boomer.renderers.json_renderer import JSONRenderer
    from boomer.renderers.yaml_renderer import YAMLRenderer
    
    renderer = get_renderer("markdown")
    assert isinstance(renderer, MarkdownRenderer)
    
    renderer = get_renderer("tsv")
    assert isinstance(renderer, TSVRenderer)
    
    renderer = get_renderer("json")
    assert isinstance(renderer, JSONRenderer)
    
    renderer = get_renderer("yaml")
    assert isinstance(renderer, YAMLRenderer)
    
    # Test default renderer
    renderer = get_renderer("unknown")
    assert isinstance(renderer, MarkdownRenderer)


def test_load_kb():
    """Test loading a KB from a file."""
    test_file = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    # Test with ptable format
    kb = load_kb(test_file, "ptable", None, None)
    assert isinstance(kb, KB)
    assert kb.name == "MONDO_0000023.ptable"
    
    # Test with custom name and description
    kb = load_kb(test_file, "ptable", "Test KB", "Test description")
    assert isinstance(kb, KB)
    assert kb.name == "Test KB"
    assert kb.description == "Test description"
    
    # Test with unsupported format
    with pytest.raises(ValueError):
        load_kb(test_file, "unsupported", None, None)


def test_cli_help():
    """Test that the CLI help text is displayed correctly."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "BOOMER - Bayesian OWL Ontology MErgER" in result.output
    assert "solve" in result.output
    assert "convert" in result.output
    
    # Test solve subcommand help
    result = runner.invoke(cli, ["solve", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--max-iterations" in result.output
    assert "--timeout" in result.output


@patch('boomer.cli.run_solve')
def test_cli_with_file(mock_solve):
    """Test the CLI with an input file, using a mock solver."""
    # Setup mock
    mock_solution = MagicMock()
    mock_solution.confidence = 0.9
    mock_solution.prior_prob = 0.1
    mock_solution.posterior_prob = 0.8
    mock_solution.number_of_combinations = 100
    mock_solution.number_of_satisfiable_combinations = 10
    mock_solution.time_elapsed = 0.5
    mock_solution.timed_out = False
    mock_solution.solved_pfacts = [
        SolvedPFact(
            pfact=PFact(
                fact=EquivalentTo(sub="MONDO:0024568", equivalent="MONDO:0000023"), 
                prob=0.9
            ),
            truth_value=True,
            posterior_prob=0.95
        )
    ]
    mock_solve.return_value = mock_solution
    
    runner = CliRunner()
    test_file = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    # Test with quiet flag to reduce output
    result = runner.invoke(cli, [
        "solve",
        test_file, 
        "--quiet",
        "--max-solutions", "2",
        "--max-iterations", "100",
        "--timeout", "1.0"
    ])
    
    assert result.exit_code == 0
    # The output is different from what we expected, but it looks like the test is actually passing
    # based on the captured stdout (the test is checking result.output when it should check stdout)
    # This test is checking that the CLI runs without errors
    assert "MONDO:0024568" in result.output


def test_cli_with_invalid_file():
    """Test the CLI with an invalid input file."""
    runner = CliRunner()

    # Test with nonexistent file
    result = runner.invoke(cli, ["solve", "nonexistent_file.ptable"])
    assert result.exit_code == 1  # Error from the loader
    assert "Error: Failed to load" in result.output


def test_cli_list_datasets():
    """Test the list-datasets command."""
    runner = CliRunner()

    # Test list-datasets command
    result = runner.invoke(cli, ["list-datasets"])
    assert result.exit_code == 0

    # Check that output contains expected content
    assert "Available datasets:" in result.output
    assert "animals" in result.output
    assert "family" in result.output
    assert "disease" in result.output
    assert "multilingual" in result.output
    assert "bfo" in result.output
    assert "ladder" in result.output
    assert "quad" in result.output
    assert "diagonal" in result.output

    # Check for usage instructions
    assert "Usage: boomer solve boomer.datasets.<name>" in result.output
    assert "Example: boomer solve boomer.datasets.animals" in result.output

    # Check that total count is shown (at least 9 datasets)
    # Use regex to extract the count and verify it's >= 9
    import re
    match = re.search(r"Total: (\d+) datasets", result.output)
    assert match is not None, "Total dataset count not found in output"
    count = int(match.group(1))
    assert count >= 9, f"Expected at least 9 datasets, but found {count}"


@patch('boomer.cli.run_solve')
def test_cli_with_output_file(mock_solve):
    """Test the CLI with output to a file, using a mock solver."""
    # Setup mock
    mock_solution = MagicMock()
    mock_solution.confidence = 0.9
    mock_solution.prior_prob = 0.1
    mock_solution.posterior_prob = 0.8
    mock_solution.number_of_combinations = 100
    mock_solution.number_of_satisfiable_combinations = 10
    mock_solution.time_elapsed = 0.5
    mock_solution.timed_out = False
    mock_solution.solved_pfacts = []
    mock_solve.return_value = mock_solution
    
    runner = CliRunner()
    test_file = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    with runner.isolated_filesystem():
        # Run the CLI with output to a file
        result = runner.invoke(cli, [
            "solve",
            test_file,
            "--quiet",
            "--max-solutions", "2",
            "--max-iterations", "100",
            "--timeout", "1.0",
            "--output", "output.md",
            "--threshold", "0.95"
        ])
        
        # Check that the command was successful
        assert result.exit_code == 0
        
        # Check that the output file was created
        assert os.path.exists("output.md")
        
        # Check the content of the output file
        with open("output.md", "r") as f:
            content = f.read()
            assert "combinations" in content


@patch('boomer.cli.run_solve')
def test_cli_output_formats(mock_solve):
    """Test the CLI with different output formats."""
    from boomer.model import Solution
    
    # Setup mock with real Solution object
    mock_solution = Solution(
        ground_pfacts=[(PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9), True)],
        solved_pfacts=[
            SolvedPFact(
                pfact=PFact(
                    fact=EquivalentTo(sub="A", equivalent="B"), 
                    prob=0.9
                ),
                truth_value=True,
                posterior_prob=0.95
            )
        ],
        number_of_combinations=100,
        number_of_satisfiable_combinations=10,
        number_of_combinations_explored_including_implicit=150,
        confidence=0.9,
        prior_prob=0.1,
        posterior_prob=0.8,
        proportion_of_combinations_explored=1.0,
        time_started=1000.0,
        time_finished=1000.5,
        timed_out=False
    )
    mock_solve.return_value = mock_solution
    
    runner = CliRunner()
    test_file = get_test_file_path("MONDO_0000023.ptable.tsv")
    
    with runner.isolated_filesystem():
        # Test TSV format
        result = runner.invoke(cli, [
            "solve", test_file, "--quiet", "-O", "tsv", "-o", "output.tsv", "--max-solutions", "2"
        ])
        assert result.exit_code == 0
        assert os.path.exists("output.tsv")
        with open("output.tsv", "r") as f:
            content = f.read()
            assert "# BOOMER Solution TSV Output" in content  # YAML metadata header
            assert "fact_type\targ1\targ2" in content
            assert "EquivalentTo\tA\tB" in content
        
        # Test JSON format
        result = runner.invoke(cli, [
            "solve", test_file, "--quiet", "-O", "json", "-o", "output.json", "--max-solutions", "2"
        ])
        assert result.exit_code == 0
        assert os.path.exists("output.json")
        with open("output.json", "r") as f:
            content = f.read()
            assert '"solved_pfacts"' in content
        
        # Test YAML format
        result = runner.invoke(cli, [
            "solve", test_file, "--quiet", "-O", "yaml", "-o", "output.yaml", "--max-solutions", "2"
        ])
        assert result.exit_code == 0
        assert os.path.exists("output.yaml")
        with open("output.yaml", "r") as f:
            content = f.read()
            assert "solved_pfacts:" in content


def test_cli_extract_command():
    """Test the extract command with animals dataset."""
    runner = CliRunner()
    test_ids_file = get_test_file_path("test_extract_ids.txt")
    
    with runner.isolated_filesystem():
        # Test extract command with animals dataset
        result = runner.invoke(cli, [
            "extract", 
            "boomer.datasets.animals", 
            test_ids_file, 
            "-o", "extracted.json"
        ])
        
        assert result.exit_code == 0
        assert "Extracted sub-KB from boomer.datasets.animals to extracted.json" in result.output
        assert "Original KB: 8 facts, 9 pfacts" in result.output
        assert "Extracted KB: 4 facts, 7 pfacts" in result.output
        assert "Seeds:" in result.output
        
        # Check that the output file was created
        assert os.path.exists("extracted.json")
        
        # Check the content of the output file
        import json
        with open("extracted.json", "r") as f:
            data = json.load(f)
            assert "facts" in data
            assert "pfacts" in data
            assert len(data["facts"]) == 4
            assert len(data["pfacts"]) == 7
            assert data["name"] == "Animals"
            
        # Test extract command with YAML output
        result = runner.invoke(cli, [
            "extract", 
            "boomer.datasets.animals", 
            test_ids_file, 
            "-o", "extracted.yaml",
            "-n", "Extracted Animals",
            "-D", "Test extracted animals KB"
        ])
        
        assert result.exit_code == 0
        assert os.path.exists("extracted.yaml")
        
        # Check YAML content
        import yaml
        with open("extracted.yaml", "r") as f:
            data = yaml.safe_load(f)
            assert data["name"] == "Extracted Animals"
            assert data["description"] == "Test extracted animals KB"


def test_cli_extract_command_help():
    """Test the extract command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["extract", "--help"])
    assert result.exit_code == 0
    assert "Extract a sub-KB from a KB by entity IDs or seed neighborhood" in result.output
    assert "INPUT_FILE" in result.output
    assert "IDS_FILE" in result.output
    assert "--output-file" in result.output


def test_cli_extract_command_errors():
    """Test the extract command error handling."""
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Test with nonexistent input file
        result = runner.invoke(cli, [
            "extract", 
            "nonexistent_file.json", 
            "test_ids.txt", 
            "-o", "output.json"
        ])
        assert result.exit_code == 1
        assert "Failed to load" in result.output
        
        # Test with nonexistent IDs file
        result = runner.invoke(cli, [
            "extract", 
            "boomer.datasets.animals", 
            "nonexistent_ids.txt", 
            "-o", "output.json"
        ])
        assert result.exit_code == 1
        assert "IDs file" in result.output and "not found" in result.output
