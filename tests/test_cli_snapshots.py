"""
CLI snapshot tests for dataset modules.

This test module runs the CLI solve command on all available dataset modules
and saves the output to snapshot files for regression testing.
"""

import os
import importlib
import tempfile
import shutil
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner

from boomer.cli import cli
from boomer.loaders import load_kb_smart
from boomer.model import KB


def discover_dataset_modules() -> List[str]:
    """
    Discover all dataset modules in boomer.datasets that have a 'kb' attribute.
    
    Returns:
        List of module names (e.g., ['animals', 'family', 'bfo'])
    """
    dataset_modules = []
    datasets_path = Path(__file__).parent.parent / "src" / "boomer" / "datasets"
    
    for py_file in datasets_path.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
            
        module_name = py_file.stem
        try:
            # Try to import the module and check if it has a kb attribute
            module = importlib.import_module(f"boomer.datasets.{module_name}")
            if hasattr(module, 'kb') and isinstance(module.kb, KB):
                dataset_modules.append(module_name)
        except (ImportError, AttributeError):
            # Skip modules that can't be imported or don't have kb
            continue
    
    return sorted(dataset_modules)


class TestCLISnapshots:
    """Test CLI output snapshots for all dataset modules."""
    
    @pytest.fixture
    def snapshots_dir(self):
        """Create and return the snapshots directory."""
        snapshots_path = Path(__file__).parent / "__snapshots__"
        snapshots_path.mkdir(exist_ok=True)
        return snapshots_path
    
    def test_dataset_snapshots(self, snapshots_dir):
        """
        Test CLI solve command on all dataset modules and save snapshots.
        
        This test runs the solve command with --output-dir option on each
        available dataset module and saves the results as snapshot files.
        The snapshots can be used for regression testing by comparing
        outputs between runs.

        TODO: avoid duplication with similar test
        """
        runner = CliRunner()
        dataset_modules = discover_dataset_modules()
        
        # Ensure we found at least some datasets
        assert len(dataset_modules) > 0, "No dataset modules found with 'kb' attribute"
        
        for module_name in dataset_modules:
            module_path = f"boomer.datasets.{module_name}"
            
            # Create a temporary directory for this dataset's output
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Run the CLI solve command with output directory
                result = runner.invoke(cli, [
                    "solve", module_path,
                    "--format", "py",  # Explicitly specify Python module format
                    "--output-dir", str(temp_path),
                    "--max-solutions", "10",  # Limit solutions for faster testing
                    "--quiet"  # Suppress progress output
                ])
                
                # Check that the command succeeded
                assert result.exit_code == 0, f"CLI failed for {module_name}: {result.output}"
                
                # Copy the generated files to snapshots directory
                dataset_snapshot_dir = snapshots_dir / module_name
                if dataset_snapshot_dir.exists():
                    shutil.rmtree(dataset_snapshot_dir)
                
                # Copy the entire output directory
                shutil.copytree(temp_path, dataset_snapshot_dir)
                
                # Verify that output files were created
                solution_files = list(dataset_snapshot_dir.glob("solution.*"))
                assert len(solution_files) > 0, f"No solution files generated for {module_name}"
                
                # Check for expected formats
                expected_formats = ["markdown", "tsv", "json", "yaml"]
                for fmt in expected_formats:
                    solution_file = dataset_snapshot_dir / f"solution.{fmt}"
                    assert solution_file.exists(), f"Missing {fmt} output for {module_name}"
                    assert solution_file.stat().st_size > 0, f"Empty {fmt} output for {module_name}"
    
    def test_snapshot_contents_basic_validation(self, snapshots_dir):
        """
        Basic validation that snapshot files contain expected content.
        
        This test performs basic sanity checks on the generated snapshots
        without hardcoding specific expected values.
        """
        dataset_modules = discover_dataset_modules()
        
        for module_name in dataset_modules:
            dataset_snapshot_dir = snapshots_dir / module_name
            
            # Skip if snapshots haven't been generated yet
            if not dataset_snapshot_dir.exists():
                pytest.skip(f"Snapshots not generated for {module_name}")
            
            # Check markdown output contains expected sections
            markdown_file = dataset_snapshot_dir / "solution.markdown"
            if markdown_file.exists():
                content = markdown_file.read_text()
                assert "combinations" in content.lower()
                assert "confidence" in content.lower()
                assert "grounding" in content.lower()
                
            # Check JSON output is valid JSON and contains expected fields
            json_file = dataset_snapshot_dir / "solution.json"
            if json_file.exists():
                import json
                try:
                    data = json.loads(json_file.read_text())
                    assert "solved_pfacts" in data
                    assert "confidence" in data
                    assert isinstance(data["confidence"], (int, float))
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON in {json_file}")
            
            # Check TSV output has proper structure
            tsv_file = dataset_snapshot_dir / "solution.tsv"
            if tsv_file.exists():
                content = tsv_file.read_text()
                lines = content.strip().split('\n')
                # Should have metadata header and TSV data
                assert len(lines) > 1
                # Look for YAML metadata header
                assert any(line.startswith('#') for line in lines[:10])
    
    @pytest.mark.parametrize("dataset_name", discover_dataset_modules())
    def test_individual_dataset_snapshot(self, dataset_name, snapshots_dir):
        """
        Test individual dataset snapshot generation.
        
        This parametrized test runs each dataset individually, making it easier
        to identify which specific dataset might be causing issues.
        """
        runner = CliRunner()
        module_path = f"boomer.datasets.{dataset_name}"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            kb = load_kb_smart(module_path, "py")
            max_solutions = 5
            max_iterations = 1000
            max_pfacts_per_clique = 100
            if kb.default_configurations:
                def_kb = kb.default_configurations["default"]
                print(f"Default configuration: {def_kb}")
                if def_kb.max_candidate_solutions:
                    max_solutions = def_kb.max_candidate_solutions
                if def_kb.max_iterations:
                    max_iterations = def_kb.max_iterations
                if def_kb.max_pfacts_per_clique:
                    max_pfacts_per_clique = def_kb.max_pfacts_per_clique

            print(f"Running with max_solutions={max_solutions}, max_iterations={max_iterations}, max_pfacts_per_clique={max_pfacts_per_clique}")

            
            # Run CLI solve command
            result = runner.invoke(cli, [
                "solve", module_path,
                "--format", "py",  # Explicitly specify Python module format
                "--output-dir", str(temp_path),
                "--max-solutions", str(max_solutions), 
                "--max-iterations", str(max_iterations),
                "--max-pfacts-per-clique", str(max_pfacts_per_clique),
                "--quiet"
            ])
            
            assert result.exit_code == 0, f"CLI failed for {dataset_name}: {result.output}"
            
            # Verify basic output structure
            solution_files = list(temp_path.glob("solution.*"))
            assert len(solution_files) >= 4, f"Expected at least 4 format outputs for {dataset_name}"
            
            # Check that components directory exists if there are sub-solutions
            components_dir = temp_path / "components"
            if components_dir.exists():
                component_files = list(components_dir.glob("solution_*.markdown"))
                # If components exist, they should have content
                if component_files:
                    for comp_file in component_files:
                        assert comp_file.stat().st_size > 0, f"Empty component file: {comp_file}"


def test_discover_dataset_modules():
    """Test the dataset module discovery function."""
    modules = discover_dataset_modules()
    
    # Should find at least the known working modules
    expected_modules = {"animals", "family", "bfo", "ladder", "diagonal", "multilingual", "quad"}
    found_modules = set(modules)
    
    assert expected_modules.issubset(found_modules), f"Missing expected modules. Found: {found_modules}"
    
    # All returned modules should be valid
    for module_name in modules:
        module = importlib.import_module(f"boomer.datasets.{module_name}")
        assert hasattr(module, 'kb')
        assert isinstance(module.kb, KB)


