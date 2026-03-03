#!/usr/bin/env python

"""
Command-line interface for BOOMER - Bayesian OWL Ontology MErgER

This module provides a command-line interface for running BOOMER on
various input formats, with the current implementation focusing on
probability tables (PTables).
"""

import sys
import time
from typing import Optional, TextIO
from pathlib import Path
import importlib
import pkgutil

try:
    import yaml
except ImportError:
    yaml = None

import click
import logging
from boomer.io import save_kb
from boomer.loaders import load_kb_smart
from boomer.model import KB, EquivalentTo, SearchConfig, Solution
from boomer.search import solve as run_solve
from boomer.renderers.markdown_renderer import MarkdownRenderer
from boomer.renderers.tsv_renderer import TSVRenderer
from boomer.renderers.json_renderer import JSONRenderer
from boomer.renderers.yaml_renderer import YAMLRenderer
from boomer.renderers.sssom_renderer import SSSOMRenderer
from boomer.renderers.obographs_renderer import OBOGraphsRenderer
from boomer.renderers.renderer import Renderer
from boomer.evaluator import evaluate_facts
from boomer.model import GridSearch
from boomer.search import grid_search
from boomer.splitter import extract_neighborhood, extract_sub_kb

logger = logging.getLogger(__name__)


FORMAT_EXTENSIONS: dict[str, str] = {
    "markdown": "markdown",
    "tsv": "tsv",
    "json": "json",
    "yaml": "yaml",
    "sssom": "sssom.tsv",
    "obographs": "obographs.json",
}


def get_renderer(format_name: str) -> Renderer:
    """Get the appropriate renderer for the specified format."""
    if format_name == "markdown":
        return MarkdownRenderer()
    elif format_name == "tsv":
        return TSVRenderer()
    elif format_name == "json":
        return JSONRenderer()
    elif format_name == "yaml":
        return YAMLRenderer()
    elif format_name == "sssom":
        return SSSOMRenderer()
    elif format_name == "obographs":
        return OBOGraphsRenderer()
    else:
        # Default to markdown for unknown formats
        return MarkdownRenderer()


def load_kb(
    input_file: str, format_name: str, name: Optional[str], description: Optional[str]
) -> KB:
    """Load a KB from the specified input file."""
    return load_kb_smart(input_file, format_name, name, description)


def write_output(output_file: Optional[str], content: str) -> None:
    """Write content to the specified output file or stdout."""
    if output_file:
        with open(output_file, "w") as f:
            f.write(content)
    else:
        click.echo(content)


def print_summary(
    kb: KB, solution, threshold: float, output: TextIO = sys.stdout
) -> None:
    """Print a summary of the solution."""
    click.echo(f"Knowledge Base: {kb.name or 'Unnamed'}", file=output)
    click.echo(f"KB num pfacts: {len(kb.pfacts)}", file=output)
    if kb.description:
        click.echo(f"Description: {kb.description}", file=output)

    click.echo("\nSearch Statistics:", file=output)
    click.echo(f"  Confidence: {solution.confidence:.4f}", file=output)
    click.echo(f"  Prior Probability: {solution.prior_prob:.4e}", file=output)
    click.echo(f"  Posterior Probability: {solution.posterior_prob:.4f}", file=output)
    click.echo(
        f"  Combinations Explored: {solution.number_of_combinations}", file=output
    )
    click.echo(
        f"  Satisfiable Combinations: {solution.number_of_satisfiable_combinations}",
        file=output,
    )
    click.echo(f"  Time Elapsed: {solution.time_elapsed:.4f} seconds", file=output)
    if solution.timed_out:
        click.echo("  Warning: Search timed out", file=output)
    click.echo(f"  Sub-solutions: {len(solution.sub_solutions)}", file=output)

    click.echo(f"\nHigh Confidence Results (threshold >= {threshold}):", file=output)
    count = 0
    for spf in solution.solved_pfacts:
        if spf.truth_value and spf.posterior_prob >= threshold:
            count += 1
            fact_str = str(spf.pfact.fact)
            click.echo(
                f"  {fact_str} (posterior: {spf.posterior_prob:.4f})", file=output
            )

    if count == 0:
        click.echo("  No results meet the threshold.", file=output)


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli():
    """BOOMER - Bayesian OWL Ontology MErgER"""
    pass


@cli.command()
@click.argument("input_file")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    default=None,
    help="Input format (auto-detected if not specified)",
)
@click.option(
    "--name", "-n", help="Name for the knowledge base (defaults to input filename)"
)
@click.option("--description", "-D", help="Description for the knowledge base")
@click.option(
    "--max-iterations",
    "-i",
    type=int,
    default=1000000,
    show_default=True,
    help="Maximum number of iterations",
)
@click.option(
    "--max-solutions",
    "-s",
    type=int,
    default=10000,
    show_default=True,
    help="Maximum number of candidate solutions",
)
@click.option(
    "--timeout", "-t", type=float, help="Maximum time in seconds to run the search"
)
@click.option(
    "--max-pfacts-per-clique",
    "-C",
    type=int,
    default=100,
    show_default=True,
    help="Maximum number of probabilistic facts per clique",
)
@click.option(
    "--exhaustive-search-depth",
    "-e",
    type=int,
    default=None,
    help="Exhaustive search depth",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    help="Output file (defaults to stdout)",
)
@click.option(
    "--format-output",
    "-O",
    type=click.Choice(["markdown", "tsv", "json", "yaml", "sssom", "obographs"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--output-dir",
    "-d",
    type=click.Path(writable=True),
    help="Output directory for intermediate solutions",
)
@click.option(
    "--threshold",
    "-T",
    type=float,
    default=0.8,
    help="Posterior probability threshold for reporting results",
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress output")
@click.option("--verbose", "-v", count=True, help="Verbose output")
def solve(
    input_file,
    format,
    name,
    description,
    max_pfacts_per_clique,
    exhaustive_search_depth,
    max_iterations,
    max_solutions,
    timeout,
    output,
    format_output,
    output_dir,
    threshold,
    quiet,
    verbose,
):
    """
    BOOMER - Bayesian OWL Ontology MErgER

    Process an input file with BOOMER to perform probabilistic reasoning.
    Supports ptable, json, yaml files and Python module paths.
    """
    # Load the KB
    try:
        kb = load_kb_smart(input_file, format, name, description)
    except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
        raise click.ClickException(f"Failed to load '{input_file}': {e}")

    logger = logging.getLogger()
    # Set handler for the root logger to output to the console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Clear existing handlers to avoid duplicate messages if function runs multiple times
    logger.handlers = []

    # Add the newly created console handler to the logger
    logger.addHandler(console_handler)
    if verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    if quiet:
        logger.setLevel(logging.ERROR)

    if not quiet:
        click.echo(
            f"Loaded KB with {len(kb.facts)} facts and {len(kb.pfacts)} probabilistic facts"
        )

    # Configure the search
    config = SearchConfig(
        max_iterations=max_iterations,
        max_candidate_solutions=max_solutions,
        max_pfacts_per_clique=max_pfacts_per_clique,
        timeout_seconds=timeout,
        exhaustive_search_depth=exhaustive_search_depth,
    )

    # Solve the KB
    start_time = time.time()
    if not quiet:
        click.echo("Starting search...")

    solution = run_solve(kb, config)
    if solution.sub_solutions:
        solution.sort_sub_solutions()
        solution.name_sub_solutions(kb)

    if not quiet:
        end_time = time.time()
        click.echo(f"Search completed in {end_time - start_time:.4f} seconds")



    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for fmt, ext in FORMAT_EXTENSIONS.items():
            renderer = get_renderer(fmt)
            output_file = output_dir / f"solution.{ext}"
            write_output(output_file, renderer.render(solution, kb))
            component_dir = output_dir / "components"
            component_dir.mkdir(parents=True, exist_ok=True)
            for i, sub_solution in enumerate(solution.sub_solutions):
                sub_solution_file = component_dir / f"solution_{i}.{ext}"
                write_output(sub_solution_file, renderer.render(sub_solution, kb))

    # Get the renderer and generate output
    renderer = get_renderer(format_output)
    rendered_output = renderer.render(solution, kb)

    # Write the output
    if output:
        write_output(output, rendered_output)

        # For structured formats, only print summary if not quiet
        # For markdown, always print summary (backward compatibility)
        if format_output == "markdown" or not quiet:
            print_summary(kb, solution, threshold)
    else:
        # Print the summary and rendered output to stdout
        print_summary(kb, solution, threshold)
        click.echo("\nFull Solution:")
        click.echo(rendered_output)

    return 0


@cli.command()
@click.argument("input_files", nargs=-1, required=True)
@click.option("--output-file", "-o", type=click.Path(writable=True), required=True, help="Output file")
@click.option(
    "--input-format",
    "-f",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    help="Input format (auto-detected from extension if not specified)",
)
@click.option(
    "--output-format",
    "-O",
    type=click.Choice(["ptable", "json", "yaml"]),
    help="Output format (auto-detected from extension if not specified)",
)
@click.option(
    "--name", "-n", help="Name for the merged knowledge base"
)
@click.option(
    "--description",
    "-D",
    help="Description for the merged knowledge base",
)
def merge(input_files, output_file, input_format, output_format, name, description):
    """
    Merge multiple KB files into a single KB.

    Takes multiple input files and combines them into a single knowledge base.
    Supports mixed input formats with auto-detection.

    Supports merging:
    - ptable (TSV probability tables)
    - json (JSON KB format)
    - yaml (YAML KB format)
    - py (Python module paths like boomer.datasets.animals)

    Input and output formats are auto-detected from file extensions if not specified.
    """
    if len(input_files) < 2:
        raise click.ClickException("At least two input files are required for merging.")
    
    output_path = Path(output_file)
    
    # Note: input_format can be None to enable per-file format detection

    # Auto-detect output format if not specified
    if output_format is None:
        ext = output_path.suffix.lower()
        if ext == ".tsv" or "ptable" in output_path.name:
            output_format = "ptable"
        elif ext == ".json":
            output_format = "json"
        elif ext in [".yaml", ".yml"]:
            output_format = "yaml"
        else:
            raise click.ClickException(
                f"Cannot auto-detect output format from '{output_file}'. Please specify --output-format."
            )

    # Load and merge all KBs
    merged_kb = None
    for input_file in input_files:
        # Load KB using smart loader
        try:
            kb = load_kb_smart(input_file, input_format)
        except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
            raise click.ClickException(f"Failed to load '{input_file}': {e}")
        
        if merged_kb is None:
            merged_kb = kb
            # Set name and description for the first KB
            if name:
                merged_kb.name = name
            elif not merged_kb.name:
                merged_kb.name = f"Merged KB from {len(input_files)} files"
            if description:
                merged_kb.description = description
        else:
            # Merge subsequent KBs
            merged_kb = merged_kb.extend(
                facts=kb.facts,
                pfacts=kb.pfacts,
                hypotheses=kb.hypotheses,
                labels=kb.labels
            )
    
    # Normalize the merged KB
    merged_kb.normalize()
    
    # Save merged KB based on output format
    if output_format == "ptable":
        raise click.ClickException(
            "ptable output format not yet implemented. Use json or yaml."
        )
    elif output_format in ["json", "yaml"]:
        save_kb(merged_kb, output_file, output_format)
        click.echo(
            f"Merged {len(input_files)} files into {output_file} ({output_format})"
        )
        click.echo(f"Final KB contains {len(merged_kb.facts)} facts and {len(merged_kb.pfacts)} probabilistic facts")
    else:
        raise click.ClickException(f"Unsupported output format: {output_format}")


@cli.command()
@click.argument("input_file")
@click.option("--output-file", "-o", type=click.Path(writable=True), required=True, help="Output file")
@click.option(
    "--input-format",
    "-f",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    help="Input format (auto-detected from extension if not specified)",
)
@click.option(
    "--output-format",
    "-O",
    type=click.Choice(["ptable", "json", "yaml"]),
    help="Output format (auto-detected from extension if not specified)",
)
@click.option(
    "--name", "-n", help="Name for the knowledge base (only used for ptable input)"
)
@click.option(
    "--description",
    "-D",
    help="Description for the knowledge base (only used for ptable input)",
)
def convert(input_file, output_file, input_format, output_format, name, description):
    """
    Convert between different KB formats.

    Supports conversion between:
    - ptable (TSV probability tables)
    - json (JSON KB format)
    - yaml (YAML KB format)
    - py (Python module paths like boomer.datasets.animals)

    Input and output formats are auto-detected from file extensions if not specified.
    """
    output_path = Path(output_file)

    # Auto-detect input format if not specified
    if input_format is None:
        try:
            from boomer.loaders import KBLoader
            input_format = KBLoader.detect_format(input_file)
        except ValueError:
            raise click.ClickException(
                f"Cannot auto-detect input format from '{input_file}'. Please specify --input-format."
            )

    # Auto-detect output format if not specified
    if output_format is None:
        ext = output_path.suffix.lower()
        if ext == ".tsv" or "ptable" in output_path.name:
            output_format = "ptable"
        elif ext == ".json":
            output_format = "json"
        elif ext in [".yaml", ".yml"]:
            output_format = "yaml"
        else:
            raise click.ClickException(
                f"Cannot auto-detect output format from '{output_file}'. Please specify --output-format."
            )

    # Load KB using smart loader
    try:
        kb = load_kb_smart(input_file, input_format, name, description)
    except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
        raise click.ClickException(f"Failed to load '{input_file}': {e}")

    # Save KB based on output format
    if output_format == "ptable":
        raise click.ClickException(
            "ptable output format not yet implemented. Use json or yaml."
        )
    elif output_format in ["json", "yaml"]:
        save_kb(kb, output_file, output_format)
        click.echo(
            f"Converted {input_file} ({input_format}) to {output_file} ({output_format})"
        )
    else:
        raise click.ClickException(f"Unsupported output format: {output_format}")


@cli.command()
@click.argument("input_file")
@click.argument("ids_file", required=False, default=None)
@click.option("--id", "entity_ids_cli", multiple=True, help="Entity ID seed (repeatable)")
@click.option("--max-hops", "-H", type=int, default=None, help="Max hops from seed (default: unlimited)")
@click.option("--output-file", "-o", type=click.Path(writable=True), required=True, help="Output file")
@click.option(
    "--input-format",
    "-f",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    help="Input format (auto-detected from extension if not specified)",
)
@click.option(
    "--output-format",
    "-O",
    type=click.Choice(["ptable", "json", "yaml"]),
    help="Output format (auto-detected from extension if not specified)",
)
@click.option(
    "--name", "-n", help="Name for the extracted knowledge base"
)
@click.option(
    "--description",
    "-D",
    help="Description for the extracted knowledge base",
)
def extract(input_file, ids_file, entity_ids_cli, max_hops, output_file, input_format, output_format, name, description):
    """
    Extract a sub-KB from a KB by entity IDs or seed neighborhood.

    Entity IDs can be provided via --id flags (repeatable) or a file (one ID
    per line).  When --id is used, the neighborhood of those seed entities is
    extracted — all transitively connected entities are included.  Use
    --max-hops to limit the BFS depth.

    \b
    Examples:
      # Seed-based neighborhood extraction
      pyboomer extract kb.yaml --id MONDO:0001234 -o cluster.yaml
      pyboomer extract kb.yaml --id MONDO:0001234 --id ORDO:123 -o cluster.yaml
      pyboomer extract kb.yaml --id MONDO:0001234 --max-hops 2 -o cluster.yaml

      # File-based exact extraction (legacy)
      pyboomer extract kb.yaml ids.txt -o sub.yaml
    """
    # Load the original KB
    try:
        kb = load_kb_smart(input_file, input_format, name, description)
    except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
        raise click.ClickException(f"Failed to load '{input_file}': {e}")

    # Collect entity IDs from --id flags and/or IDS_FILE
    entity_ids: set[str] = set(entity_ids_cli)

    if ids_file is not None:
        try:
            with open(ids_file, 'r') as f:
                entity_ids |= {line.strip() for line in f if line.strip()}
        except FileNotFoundError:
            raise click.ClickException(f"IDs file '{ids_file}' not found")

    if not entity_ids:
        raise click.ClickException("No entity IDs provided. Use --id flags or an IDS_FILE argument.")

    # Extract sub-KB
    if entity_ids_cli or max_hops is not None:
        # Neighborhood mode: expand from seeds
        sub_kb = extract_neighborhood(kb, entity_ids, max_hops=max_hops)
    else:
        # Legacy file mode: exact entity match
        sub_kb = extract_sub_kb(kb, entity_ids, include_labels=True)

    # Set name and description if provided
    if name:
        sub_kb.name = name
    elif not sub_kb.name:
        sub_kb.name = f"Extracted from {Path(input_file).name}"

    if description:
        sub_kb.description = description
    elif not sub_kb.description:
        sub_kb.description = f"Sub-KB extracted from {input_file} using {len(entity_ids)} seed(s)"

    # Auto-detect output format if not specified
    output_path = Path(output_file)
    if output_format is None:
        ext = output_path.suffix.lower()
        if ext == ".tsv" or "ptable" in output_path.name:
            output_format = "ptable"
        elif ext == ".json":
            output_format = "json"
        elif ext in [".yaml", ".yml"]:
            output_format = "yaml"
        else:
            raise click.ClickException(
                f"Cannot auto-detect output format from '{output_file}'. Please specify --output-format."
            )

    # Save extracted KB
    if output_format == "ptable":
        raise click.ClickException(
            "ptable output format not yet implemented. Use json or yaml."
        )
    elif output_format in ["json", "yaml"]:
        save_kb(sub_kb, output_file, output_format)
        click.echo(
            f"Extracted sub-KB from {input_file} to {output_file} ({output_format})"
        )
        click.echo(f"Original KB: {len(kb.facts)} facts, {len(kb.pfacts)} pfacts")
        click.echo(f"Extracted KB: {len(sub_kb.facts)} facts, {len(sub_kb.pfacts)} pfacts")
        click.echo(f"Seeds: {sorted(entity_ids)}")
    else:
        raise click.ClickException(f"Unsupported output format: {output_format}")


@cli.command("eval")
@click.argument("kb_file")
@click.argument("solution_file")
@click.option("--label-kb", "-l", help="Path to a KB file with labels")
@click.option(
    "--kb-format", "-k",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    default=None,
    help="Format for the gold KB (auto-detected if not specified)"
)
@click.option(
    "--output-file", "-o", type=click.Path(writable=True), required=True, help="Output file"
)
@click.option("--pr-filter", "-p", default=0.5, help="Posterior probability threshold for filtering predicted facts")
@click.option("--equiv-only", "-E", is_flag=True, help="Only evaluate equivalent-to facts")
@click.option(
    "--solution-format", "-f",
    type=click.Choice(["json", "yaml"]),
    default=None,
    help="Format for the solution file (auto-detected from extension if not specified)"
)
def eval_(kb_file, solution_file, kb_format, solution_format, output_file, equiv_only, label_kb, pr_filter):
    """
    Evaluate predicted facts (from a BOOMER Solution) against gold facts in a KB.

    The KB file must contain ground-truth facts in kb.facts.
    The solution file must be a JSON or YAML serialization of a BOOMER Solution
    (i.e., include solved_pfacts).
    """
    try:
        kb = load_kb_smart(kb_file, kb_format)
    except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
        raise click.ClickException(f"Failed to load KB '{kb_file}': {e}")
    
    if label_kb:
        try:
            label_kb = load_kb_smart(label_kb, "yaml")
        except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
            raise click.ClickException(f"Failed to load label KB '{label_kb}': {e}")
    else:
        label_kb = kb

    sol_path = Path(solution_file)
    sol_fmt = solution_format
    if sol_fmt is None:
        ext = sol_path.suffix.lower()
        if ext == ".json":
            sol_fmt = "json"
        elif ext in [".yaml", ".yml"]:
            sol_fmt = "yaml"
        else:
            raise click.ClickException(
                f"Cannot auto-detect solution format from '{solution_file}'. "
                "Please specify --solution-format."
            )

    try:
        content = sol_path.read_text(encoding="utf-8")
    except Exception as e:
        raise click.ClickException(f"Failed to read solution file '{solution_file}': {e}")

    try:
        if sol_fmt == "json":
            solution = Solution.model_validate_json(content)
        else:
            if yaml is None:
                raise click.ClickException("PyYAML is required to load YAML solution files.")
            sol_dict = yaml.safe_load(content)
            solution = Solution.model_validate(sol_dict)
    except Exception as e:
        raise click.ClickException(f"Failed to parse solution: {e}")

    predicted = [
        sp.pfact.fact
        for sp in solution.solved_pfacts
        if sp.truth_value is True and sp.posterior_prob >= pr_filter
    ]

    typs = []
    if equiv_only:
        typs.append(EquivalentTo.__name__)
    print(f"Evaluating {len(kb.facts)} facts and {len(predicted)} predicted facts; types: {typs}")
    stats = evaluate_facts(kb.facts, predicted, types=typs)

    click.echo("Evaluation results:")
    click.echo(f"  True positives:  {stats.tp}")
    click.echo(f"  False positives: {stats.fp}")
    click.echo(f"  False negatives: {stats.fn}")
    click.echo(f"  Precision:       {stats.precision:.4f}")
    click.echo(f"  Recall:          {stats.recall:.4f}")
    click.echo(f"  F1-score:        {stats.f1:.4f}")


@cli.command("grid-search")
@click.argument("kb_file")
@click.argument("grid_file")
@click.option(
    "--kb-format", "-k",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    default=None,
    help="Format for the KB (auto-detected if not specified)",
)
@click.option(
    "--eval-kb-file", "-e",
    help="KB file with gold facts for evaluation",
)
@click.option(
    "--eval-kb-format", "-f",
    type=click.Choice(["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]),
    default=None,
    help="Format for the evaluation KB (auto-detected if not specified)",
)
@click.option(
    "--output-file", "-o",
    type=click.Path(writable=True),
    required=True,
    help="Output file for serialized grid search results",
)
@click.option(
    "--output-dir", "-d",
    type=click.Path(writable=True),
    help="Output directory for intermediate solutions",
)
@click.option(
    "--output-format", "-O",
    type=click.Choice(["json", "yaml"]),
    default=None,
    help="Output format for grid search results",
)
def grid_search_cli(
    kb_file,
    grid_file,
    kb_format,
    eval_kb_file,
    eval_kb_format,
    output_file,
    output_format,
    output_dir,
):
    """
    Perform a grid search over search configurations specified in GRID_FILE.

    GRID_FILE must be a JSON or YAML file describing a GridSearch (base configs
    and configuration_matrix).  Optionally evaluate each run against gold KB.
    """
    # Load primary KB
    try:
        kb = load_kb_smart(kb_file, kb_format)
    except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
        raise click.ClickException(f"Failed to load KB '{kb_file}': {e}")

    # Load grid spec
    grid_path = Path(grid_file)
    try:
        raw = grid_path.read_text(encoding="utf-8")
    except Exception as e:
        raise click.ClickException(f"Failed to read grid spec '{grid_file}': {e}")
    ext = grid_path.suffix.lower()
    if ext == ".json":
        grid = GridSearch.model_validate_json(raw)
    elif ext in (".yaml", ".yml"):
        if yaml is None:
            raise click.ClickException(
                "PyYAML is required to load YAML grid spec."
            )
        grid = GridSearch.model_validate(yaml.safe_load(raw))
    else:
        raise click.ClickException(
            f"Cannot auto-detect grid spec format from '{grid_file}'. Use .json or .yaml."
        )

    # Optional evaluation KB
    eval_kb = None
    if eval_kb_file:
        try:
            eval_kb = load_kb_smart(eval_kb_file, eval_kb_format)
        except (ValueError, ImportError, AttributeError, FileNotFoundError) as e:
            raise click.ClickException(f"Failed to load eval KB '{eval_kb_file}': {e}")

    # Perform the grid search
    result = grid_search(kb, grid, eval_kb)

    # Serialize output
    out_path = Path(output_file)
    fmt = output_format
    if fmt is None:
        sfx = out_path.suffix.lower()
        if sfx == ".json":
            fmt = "json"
        elif sfx in (".yaml", ".yml"):
            fmt = "yaml"
        else:
            raise click.ClickException(
                f"Cannot auto-detect output format from '{output_file}'. Use --output-format."
            )
    if fmt == "json":
        content = result.model_dump_json(indent=2)
    else:
        if yaml is None:
            raise click.ClickException("PyYAML is required to write YAML output.")
        content = yaml.dump(result.model_dump(), sort_keys=False)

    write_output(output_file, content)
    click.echo(f"Grid search saved to {output_file} ({fmt}), {len(result.results or [])} runs recorded.")

    if output_dir:
        if not isinstance(output_dir, Path):
            output_dir = Path(output_dir)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        with open(output_dir / "grid_search.json", "w") as f:
            f.write(result.model_dump_json(indent=2))
        with open(output_dir / "grid_search.yaml", "w") as f:
            f.write(yaml.dump(result.model_dump(), sort_keys=False))
        with open(output_dir / "grid_search.tsv", "w") as f:
            import pandas as pd
            df = pd.DataFrame(result.to_flat_dicts())
            df.to_csv(f, sep="\t", index=False)

        for i, r in enumerate(result.results):
            sol_path = Path(output_dir) / f"solution_{i}.json"
            sol_path.write_text(r.result.model_dump_json(indent=2))
            ev_path = Path(output_dir) / f"evaluation_{i}.json"
            if r.evaluation:
                ev_path.write_text(r.evaluation.model_dump_json(indent=2))

@cli.command(name="list-datasets")
def list_datasets():
    """List all available built-in datasets."""
    import boomer.datasets

    click.echo("Available datasets:")
    click.echo()

    datasets = []
    for importer, modname, ispkg in pkgutil.iter_modules(boomer.datasets.__path__):
        if not ispkg and not modname.startswith("_"):
            try:
                module = importlib.import_module(f"boomer.datasets.{modname}")

                # Get description from module docstring or kb description
                description = ""
                if hasattr(module, "__doc__") and module.__doc__:
                    description = module.__doc__.strip().split("\n")[0]
                elif hasattr(module, "kb") and hasattr(module.kb, "description"):
                    description = module.kb.description or ""

                datasets.append((modname, description))
            except Exception:
                # Skip modules that can't be imported
                continue

    # Sort by name
    datasets.sort(key=lambda x: x[0])

    # Display datasets
    for name, desc in datasets:
        if desc:
            click.echo(f"  {name:<20} - {desc}")
        else:
            click.echo(f"  {name}")

    click.echo()
    click.echo(f"Total: {len(datasets)} datasets")
    click.echo()
    click.echo("Usage: boomer solve boomer.datasets.<name>")
    click.echo("Example: boomer solve boomer.datasets.animals")


# Make solve the default command
cli.add_command(solve, name="solve")

def main():
    """Entry point that defaults to solve command if no subcommand is given."""
    import sys

    # If no arguments or first arg doesn't look like a subcommand, prepend 'solve'
    args = sys.argv[1:]
    if not args or (
        args[0]
        and not args[0].startswith("-")
        and args[0] not in ["solve", "convert", "merge", "extract", "eval", "grid-search", "list-datasets", "--help", "-h"]
    ):
        # Check if first arg looks like a file path (exists or has extension)
        if args and (Path(args[0]).exists() or "." in args[0]):
            sys.argv.insert(1, "solve")

    cli()


if __name__ == "__main__":
    main()  # pragma: no cover
